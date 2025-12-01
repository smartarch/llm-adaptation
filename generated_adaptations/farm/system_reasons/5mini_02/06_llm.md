Reasoning and adaptation strategy

Goals to improve damage reduction
- Always fully protect the most threatened field using the closest and/or already-committed drones.
- Prefer stability: keep drones already protecting or moving to a field (to reduce churn).
- Maximize the number of fully protected fields (full protection causes birds to flee).
- Avoid overprotection: never assign more drones than required to a field.
- Keep at least half the drones protecting when possible.
- When choosing additional fields to protect, prefer fields that require few extra drones to reach full protection and have high threat (better threat-per-drone).
- If extra drones are needed to hit the "half protecting" rule, prefer idle or unassigned drones first, and as a last resort reassign the least-critical protectors (those far from their field or protecting low-threat fields).

Key selection priorities for a field (lower tuple is better):
1. Drones already protecting that specific field.
2. Drones moving to that specific field.
3. Idle drones.
4. Drones moving elsewhere.
5. Drones protecting other fields.

This biases selection to keep existing protectors and reduces unnecessary switching.

Now the code implementing the strategy:

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved SmartFarm adaptation that:
    - Always fully protects the most threatened field using closest/committed drones.
    - Attempts to fully protect additional fields based on threat-per-drone (favoring small deficits).
    - Ensures at least half of drones are protecting when possible.
    - Minimizes churn by preferring drones already protecting/moving to the same field.
    - Never overprotects a field.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        # Ensure idle group exists or fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Gather threatened fields (>0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threat -> idle all
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Map centers and quick lookup
        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        # Choose primary field: highest threat; tie-break by smaller required drones to get protection faster
        fields.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = fields[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil half

        # Classify drones by observable state
        protecting = []
        moving = []
        idle = []
        other = []
        for d in components:
            st = getattr(d, "state", None)
            if st == "protecting":
                protecting.append(d)
            elif st == "moving_to_field":
                moving.append(d)
            elif st == "idle":
                idle.append(d)
            else:
                other.append(d)

        # Count currently protecting per field based on observed state (not assignments)
        current_protectors_state = {f.id: 0 for f in fields}
        for d in protecting:
            tid = getattr(d, "target_id", None)
            if tid in current_protectors_state:
                current_protectors_state[tid] += 1

        # Helper: group name for field (fallback to idle_group if not present)
        def protect_group(field):
            g = f"protecting {field.id}"
            return g if g in group_ids else idle_group

        # Priority key for selecting drones for a field
        def select_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            ctr = centers[field.id]
            d = distance(drone, ctr)
            if st == "protecting" and tid == field.id:
                rank = 0
            elif st == "moving_to_field" and tid == field.id:
                rank = 1
            elif st == "idle":
                rank = 2
            elif st == "moving_to_field":
                rank = 3
            elif st == "protecting":
                rank = 4
            else:
                rank = 5
            return (rank, d)

        # Initialize assignment map and unassigned set
        assignments = {}
        unassigned = set(components)

        # 1) Assign primary field first (up to its cap), picking best candidates from unassigned
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, primary))
            chosen = candidates[:primary_cap]
            for d in chosen:
                assignments[d] = protect_group(primary)
                unassigned.remove(d)

        # 2) Try to fully protect other fields.
        # Compute baseline currently protecting for each field (from observed state)
        baseline_state = {f.id: current_protectors_state.get(f.id, 0) for f in fields}

        # Build list of other fields with need and score (threat per needed drone)
        other_fields = [f for f in fields if f.id != primary.id]
        needs = []
        for f in other_fields:
            cap = getattr(f, "drones_for_full_protection", 0)
            already = baseline_state.get(f.id, 0)
            # Consider already-assigned to this field as well
            already += sum(1 for d, g in assignments.items() if g == protect_group(f))
            need = max(0, cap - already)
            if cap > 0:
                # if need==0, give very high score so we prioritize keeping it
                score = f.threat_level / (need if need > 0 else 1e-6)
                # prefer small need when tied by threat-per-drone
                needs.append((score, need, f))
        needs.sort(key=lambda x: (x[0], -x[1]), reverse=True)

        for score, need, f in needs:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))
            chosen = candidates[:need]
            for d in chosen:
                assignments[d] = protect_group(f)
                unassigned.remove(d)

        # 3) Ensure at least half drones are protecting.
        def count_protecting(assigns):
            return sum(1 for d, g in assigns.items() if isinstance(g, str) and g.startswith("protecting "))

        protecting_count = count_protecting(assignments) + sum(1 for d in protecting if d not in assignments and getattr(d, "target_id", None) in current_protectors_state)
        if protecting_count < min_protectors:
            need_more = min_protectors - protecting_count
            # First use unassigned drones (prefer those best for high-threat fields)
            # Choose target field order: fields sorted by threat descending
            fields_by_threat = sorted(fields, key=lambda f: f.threat_level, reverse=True)
            # Fill by assigning to highest threat fields that have protecting groups available (without exceeding caps)
            for f in fields_by_threat:
                if need_more <= 0:
                    break
                grp = protect_group(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                # current assigned to this group
                assigned_now = sum(1 for d, g in assignments.items() if g == grp)
                # plus observed protecting state for this field that we haven't assigned
                observed = sum(1 for d in protecting if getattr(d, "target_id", None) == f.id and d not in assignments)
                cur_total = assigned_now + observed
                free_slots = max(0, cap - cur_total)
                # if no slots but still need to increase protecting_count we can allow partial protection (assign to this field even if not filling cap)
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))
                chosen = candidates[:take]
                for d in chosen:
                    assignments[d] = grp
                    unassigned.remove(d)
                    need_more -= 1
                # loop continues until need_more satisfied

            # If still need_more, as last resort reassign some protecting drones from non-primary fields
            if need_more > 0:
                # Build candidate list of drones currently protecting non-primary fields (prefer low-threat and far distance)
                steal_candidates = []
                for d in components:
                    st = getattr(d, "state", None)
                    if st != "protecting":
                        continue
                    tid = getattr(d, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    f = fields_by_id.get(tid)
                    if not f:
                        continue
                    # penalty: lower threat and larger distance are better to steal (lower cost)
                    pen = f.threat_level - 0.001 * distance(d, centers[f.id])
                    # lower pen -> better to steal -> sort ascending
                    steal_candidates.append((pen, d, f))
                steal_candidates.sort(key=lambda x: (x[0], distance(x[1], centers[x[2].id])))
                for pen, d, f in steal_candidates:
                    if need_more <= 0:
                        break
                    # Ensure stealing won't drop that field under its cap (i.e., leave it still fully protected)
                    grp = protect_group(f)
                    cap = getattr(f, "drones_for_full_protection", 0)
                    # count assigned to that group (our assignments) + observed protecting drones excluding d
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    observed = sum(1 for comp in protecting if getattr(comp, "target_id", None) == f.id and comp not in assignments and comp is not d)
                    total_if_stolen = assigned_now + observed
                    if total_if_stolen >= cap:
                        # safe to steal
                        assignments[d] = protect_group(primary)
                        need_more -= 1
                        # if we removed explicit assignment elsewhere, we handle final trimming later

        # 4) Keep unassigned drones on their current target if that target is still a protected field and not over capacity
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid and tid in fields_by_id:
                grp = f"protecting {tid}"
                if grp in group_ids:
                    f = fields_by_id[tid]
                    cap = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    observed = sum(1 for comp in protecting if getattr(comp, "target_id", None) == tid and comp not in assignments)
                    if assigned_now + observed < cap:
                        assignments[d] = grp
                        unassigned.remove(d)

        # Remaining unassigned -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.remove(d)

        # 5) Final enforcement: trim any protecting group beyond its cap (keep the best ones by priority)
        for f in fields:
            grp = protect_group(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            # sort keepers by selection priority (want to keep those already protecting/moving to this field and closer)
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 6) Issue assignments (ensure group exists, else idle)
        for d in components:
            grp = assignments.get(d, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(d, grp)