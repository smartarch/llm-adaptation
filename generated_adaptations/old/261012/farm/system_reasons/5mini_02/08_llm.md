Reasoning and adaptation strategy

Summary of improvements
- Keep the original rules: always fully protect the most threatened field with the closest drones, avoid overprotection, and try to keep at least half the drones protecting.
- Reduce churn by remembering previous assignments and preferring to keep drones on the same group when it doesn't harm primary protection.
- When selecting drones for a field, prefer (in order): drones already protecting that field, drones moving to that field, drones previously assigned to that group in our own last decision, idle drones, then other drones — with distance as a secondary tiebreaker.
- After fully protecting the primary field, try to fully protect additional fields prioritized by threat-per-needed-drone (maximize number of full protections).
- If fewer than half the drones are protecting, fill the gap first with unassigned/idle drones (closest to high-threat fields), and only as a last resort reassign protectors from the least-critical fields (far from their fields or low-threat).
- Always enforce caps (drones_for_full_protection) and never overprotect.
- Persist the last assignments to bias future choices and enforce stability.

The code below implements these ideas. It stores previous assignments per component (by Python id) and uses that to prefer stability. It guarantees every component is assigned to exactly one valid group (falls back to "idle" when a protecting group is not present in group_ids).

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved strategy that:
    - Always fully protects the most threatened field with the closest (and preferably already-committed) drones.
    - Prioritizes full protection of additional fields by threat-per-needed-drone.
    - Ensures at least half of drones are protecting whenever possible.
    - Reduces churn by preferring previous assignments and drones already protecting/moving to the target.
    - Prevents overprotection and reuses drones efficiently.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map from component identity to previously assigned group name (string)
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        def protecting_group_for(field):
            g = f"protecting {field.id}"
            return g if g in group_ids else idle_group

        # Ensure 'idle' group available
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # If no threats, idle all drones
        if not threatened:
            for c in components:
                environment.assign_group(c, idle_group)
                self.prev_assignments[id(c)] = idle_group
            return

        # Precompute centers
        centers = {f.id: center(f) for f in threatened}
        fields_by_id = {f.id: f for f in threatened}

        # Choose primary field: highest threat_level; tie-breaker fewer drones_for_full_protection (faster to protect)
        threatened.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = threatened[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil(total/2)

        # Count observed protecting drones by target (state == "protecting")
        observed_protectors_by_field = {f.id: 0 for f in threatened}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in observed_protectors_by_field:
                    observed_protectors_by_field[tid] += 1

        # Utility: priority key for selecting drones for a field.
        # Lower tuple -> more preferred.
        # Order preference:
        # 0: currently protecting this field
        # 1: moving_to_field toward this field
        # 2: previously assigned by our controller to protect this field
        # 3: idle
        # 4: moving elsewhere
        # 5: protecting other field
        # 6: other
        def select_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            prev = self.prev_assignments.get(id(drone))
            pref_prev = 0 if prev == f"protecting {field.id}" else 1
            dist = distance_to(drone, centers[field.id])
            if st == "protecting" and tid == field.id:
                state_rank = 0
            elif st == "moving_to_field" and tid == field.id:
                state_rank = 1
            elif prev == f"protecting {field.id}":
                state_rank = 2
            elif st == "idle":
                state_rank = 3
            elif st == "moving_to_field":
                state_rank = 4
            elif st == "protecting":
                state_rank = 5
            else:
                state_rank = 6
            # Combine state_rank, whether we had previously assigned this group (prefer prev), distance
            prev_bonus = 0 if prev == f"protecting {field.id}" else 1
            return (state_rank, prev_bonus, dist)

        # Start assignment process
        assignments = {}
        unassigned = set(components)

        # 1) Assign primary field fully (up to cap) using best candidates
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, primary))
            chosen = candidates[:primary_cap]
            for d in chosen:
                grp = protecting_group_for(primary)
                assignments[d] = grp
                unassigned.discard(d)

        # 2) Attempt to fully protect other fields by threat-per-needed heuristic
        # Compute baseline of how many are already effectively protecting each field:
        # observed_protectors_by_field (from state) + already assigned to that group in assignments
        baseline_assigned = {}
        for f in threatened:
            grp = protecting_group_for(f)
            assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
            observed = observed_protectors_by_field.get(f.id, 0)
            baseline_assigned[f.id] = assigned_now + observed

        # Build list of candidate fields (excluding primary) with their need and score
        field_candidates = []
        for f in threatened:
            if f.id == primary.id:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            already = baseline_assigned.get(f.id, 0)
            need = max(0, cap - already)
            # Score: threat per needed drone (higher is better). If need==0, super-high score
            score = f.threat_level / (need if need > 0 else 1e-6)
            # Also prefer smaller need as tie-breaker
            field_candidates.append((score, -need, need, f))
        field_candidates.sort(reverse=True)

        for score, negneed, need, f in field_candidates:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))
            chosen = candidates[:need]
            for d in chosen:
                grp = protecting_group_for(f)
                assignments[d] = grp
                unassigned.discard(d)

        # 3) Ensure at least half drones protect: compute current protecting count
        def current_protecting_count(assign_map):
            # Count assignments to protecting groups + observed protecting drones not in assignments
            assigned_protect = sum(1 for g in assign_map.values() if isinstance(g, str) and g.startswith("protecting "))
            # Observed protecting drones that we didn't include in assignments (they are protecting already)
            observed_extra = 0
            for c in components:
                if c in assign_map:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) in fields_by_id:
                    observed_extra += 1
            return assigned_protect + observed_extra

        protecting_count = current_protecting_count(assignments)
        if protecting_count < min_protectors:
            need_more = min_protectors - protecting_count
            # First use unassigned drones: assign them to highest-threat fields, prefer ones that can reach full protection or increase full fields
            # Order fields by threat descending
            threat_order = sorted(threatened, key=lambda f: f.threat_level, reverse=True)
            for f in threat_order:
                if need_more <= 0 or not unassigned:
                    break
                grp = protecting_group_for(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                # currently assigned to this group
                assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                observed = observed_protectors_by_field.get(f.id, 0)
                current_total = assigned_now + observed
                free_slots = max(0, cap - current_total)
                # If free_slots > 0, assign into those; else allow partial assignments if necessary to reach min_protectors
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))
                chosen = candidates[:take]
                for d in chosen:
                    assignments[d] = grp
                    unassigned.discard(d)
                    need_more -= 1
            # If still need_more, as last resort reassign some protecting drones from non-primary fields
            if need_more > 0:
                # Build stealable list: protecting drones protecting non-primary fields
                steal_list = []
                for c in components:
                    if getattr(c, "state", None) != "protecting":
                        continue
                    tid = getattr(c, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    field_obj = fields_by_id.get(tid)
                    if not field_obj:
                        continue
                    # penalty: low threat and far distance -> better to steal
                    pen = field_obj.threat_level - 0.001 * distance_to(c, centers[tid])
                    steal_list.append((pen, c, field_obj))
                steal_list.sort(key=lambda x: (x[0], distance_to(x[1], centers[x[2].id])))
                for pen, c, f in steal_list:
                    if need_more <= 0:
                        break
                    grp_from = protecting_group_for(f)
                    # count how many would remain protecting if we take this drone away
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp_from)
                    observed = sum(1 for comp in components if comp not in assignments and getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == f.id and comp is not c)
                    total_if_stolen = assigned_now + observed
                    cap = getattr(f, "drones_for_full_protection", 0)
                    # Only steal if total_if_stolen >= cap (i.e., field remains fully protected) or if field has surplus
                    if total_if_stolen >= cap:
                        # Reassign c to primary (or any high-threat) to increase protecting_count (it was counted as protecting already)
                        assignments[c] = protecting_group_for(primary)
                        if c in unassigned:
                            unassigned.discard(c)
                        need_more -= 1

        # 4) Try to keep unassigned drones on their current target if sensible (reduces churn)
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid and tid in fields_by_id:
                grp = protecting_group_for(fields_by_id[tid])
                if grp in group_ids:
                    f = fields_by_id[tid]
                    cap = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    observed = observed_protectors_by_field.get(f.id, 0)
                    if assigned_now + observed < cap:
                        assignments[d] = grp
                        unassigned.discard(d)

        # 5) Remaining unassigned -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.discard(d)

        # 6) Final enforcement: ensure no protecting group is above its cap; trim worst candidates (by priority)
        for f in threatened:
            grp = protecting_group_for(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            # Sort keepers by selection key (prefer those already protecting/moving/prev assigned and closer)
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 7) Issue assignments and store previous assignments for stability biasing
        for c in components:
            grp = assignments.get(c, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(c, grp)
            self.prev_assignments[id(c)] = grp