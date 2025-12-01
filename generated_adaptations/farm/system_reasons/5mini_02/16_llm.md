Reasoning and adaptation strategy

Improvements over the previous submission
- Keep the hard rules: always fully protect the highest-threat field using as many drones as required, prefer closest drones, never overprotect, and use at least half of drones for protection whenever possible.
- Increase stability: prefer drones already protecting or moving to a field and prefer drones that this controller assigned in the previous step (persisted per-component).
- When choosing additional fields to protect, prefer fields that give higher "threat per extra drone" (i.e., those that need few extra drones to reach full protection but have decent threat).
- Fill the "at least half protecting" requirement by using idle/unassigned drones first; only as a last resort reassign protectors from non-primary fields if it doesn't drop those fields below full protection.
- Always call environment.assign_group for every drone and fall back to the idle group if a protect group name is missing.

Implementation below follows this plan and stores previous assignments to bias future choices toward stability.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    SmartFarmAdaptation: improved stability and field-selection heuristics.

    Key rules implemented:
    - Fully protect the highest-threat field using closest/committed drones (prefer already protecting/moving/previously assigned).
    - Try to fully protect additional fields prioritized by threat-per-needed-drone.
    - Never assign more drones than a field's drones_for_full_protection.
    - Keep at least half the drones protecting whenever possible (use idle/unassigned first; only steal as last resort).
    - Persist previous assignments to reduce churn.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist previous assignment per component id for stability
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        # Determine idle group fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Threatened fields (only these get protecting groups)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threatened fields -> idle all drones
            for c in components:
                environment.assign_group(c, idle_group)
                self.prev_assignments[id(c)] = idle_group
            return

        # Precompute centers and lookup
        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        # Primary field: highest threat_level (tie-breaker: fewer required drones -> faster to secure)
        fields.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = fields[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil(total/2)

        # Observed protecting drones per field from drone state
        observed_protecting = {f.id: 0 for f in fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in observed_protecting:
                    observed_protecting[tid] += 1

        # Helper: compute group name for protecting a field (fallback to idle if group missing)
        def protect_group(f):
            g = f"protecting {f.id}"
            return g if g in group_ids else idle_group

        # Selection priority for a drone for a given field:
        # Lower tuple is preferred.
        # Preference order:
        #   0: currently protecting that field
        #   1: moving to that field
        #   2: previously assigned by our controller to that field
        #   3: idle
        #   4: moving elsewhere
        #   5: protecting other field
        #   6: other
        def selection_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            prev = self.prev_assignments.get(id(drone))
            d = dist(drone, centers[field.id])
            if st == "protecting" and tid == field.id:
                rank = 0
            elif st == "moving_to_field" and tid == field.id:
                rank = 1
            elif prev == f"protecting {field.id}":
                rank = 2
            elif st == "idle":
                rank = 3
            elif st == "moving_to_field":
                rank = 4
            elif st == "protecting":
                rank = 5
            else:
                rank = 6
            prev_bonus = 0 if prev == f"protecting {field.id}" else 1
            return (rank, prev_bonus, d)

        # Start with all drones unassigned
        assignments = {}
        unassigned = set(components)

        # 1) Secure primary field (up to its cap) using best candidates from unassigned
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda c: selection_key(c, primary))
            chosen = candidates[:primary_cap]
            for c in chosen:
                assignments[c] = protect_group(primary)
                unassigned.discard(c)

        # 2) Try to fully protect other fields
        # Baseline protection per field = observed protecting + already assigned
        baseline = {}
        for f in fields:
            grp = protect_group(f)
            assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
            baseline[f.id] = assigned_now + observed_protecting.get(f.id, 0)

        # Build candidates: (score, need, field) where score = threat / needed (higher better)
        field_candidates = []
        for f in fields:
            if f.id == primary.id:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            already = baseline.get(f.id, 0)
            need = max(0, cap - already)
            score = f.threat_level / (need if need > 0 else 1e-6)
            field_candidates.append((score, need, f))
        # sort by score desc, tie-break smaller need
        field_candidates.sort(key=lambda t: (t[0], -t[1]), reverse=True)

        for score, need, f in field_candidates:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            # pick best 'need' drones for this field
            cand = sorted(list(unassigned), key=lambda c: selection_key(c, f))[:need]
            for c in cand:
                assignments[c] = protect_group(f)
                unassigned.discard(c)

        # Helper to count protecting drones (assignments + observed protecting not included in assignments)
        def count_protecting(assigns):
            assigned_prot = sum(1 for g in assigns.values() if isinstance(g, str) and g.startswith("protecting "))
            observed_extra = 0
            for d in components:
                if d in assigns:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fields_by_id:
                    observed_extra += 1
            return assigned_prot + observed_extra

        # 3) Ensure at least half the drones are protecting
        protecting_count = count_protecting(assignments)
        if protecting_count < min_protectors:
            need_more = min_protectors - protecting_count
            # (a) Use unassigned drones: assign to highest-threat fields with capacity
            threat_order = sorted(fields, key=lambda f: f.threat_level, reverse=True)
            for f in threat_order:
                if need_more <= 0 or not unassigned:
                    break
                grp = protect_group(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                observed = observed_protecting.get(f.id, 0)
                free_slots = max(0, cap - (assigned_now + observed))
                # If no free slots but still need_more, we may still assign partial protection to increase protecting count
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                selected = sorted(list(unassigned), key=lambda c: selection_key(c, f))[:take]
                for c in selected:
                    assignments[c] = grp
                    unassigned.discard(c)
                    need_more -= 1
            # (b) Last resort: steal protectors from non-primary fields if safe (won't drop them below cap)
            if need_more > 0:
                steal_candidates = []
                for d in components:
                    if getattr(d, "state", None) != "protecting":
                        continue
                    tid = getattr(d, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    f = fields_by_id.get(tid)
                    if not f:
                        continue
                    # prefer stealing from lower-threat fields and drones that are farther from their field
                    penalty = (f.threat_level, -dist(d, centers[tid]))
                    steal_candidates.append((penalty, d, f))
                steal_candidates.sort(key=lambda x: (x[0][0], x[0][1]))
                for _, d, f in steal_candidates:
                    if need_more <= 0:
                        break
                    grp_from = protect_group(f)
                    # compute how many would remain if we remove d
                    total_current = sum(1 for comp in components if ((getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == f.id) or (assignments.get(comp) == grp_from)))
                    cap_from = getattr(f, "drones_for_full_protection", 0)
                    if total_current - 1 >= cap_from:
                        # safe to steal
                        assignments[d] = protect_group(primary)
                        # ensure it's removed from unassigned if present
                        unassigned.discard(d)
                        need_more -= 1

        # 4) Keep remaining unassigned drones on their current target if that helps (reduces churn)
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid and tid in fields_by_id:
                f = fields_by_id[tid]
                grp = protect_group(f)
                if grp in group_ids:
                    cap = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    observed = observed_protecting.get(f.id, 0)
                    if assigned_now + observed < cap:
                        assignments[d] = grp
                        unassigned.discard(d)

        # 5) Remaining unassigned -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.discard(d)

        # 6) Final enforcement: trim any group above cap, keeping best candidates
        for f in fields:
            grp = protect_group(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            # keep best 'cap' drones by selection_key
            assigned_list.sort(key=lambda d: selection_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 7) Issue assignments (must call for every component) and store prev assignments
        for c in components:
            grp = assignments.get(c, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(c, grp)
            self.prev_assignments[id(c)] = grp