Reasoning and adaptation strategy

I'll keep the same high-level rules but improve selection stability and efficiency:

- Always fully protect the most threatened field (highest threat_level) using the closest and most-committed drones.
- Prefer drones already protecting or moving to the chosen field; also prefer drones we previously assigned to that field (to reduce churn).
- After the primary field is satisfied, try to fully protect additional fields prioritized by a threat-per-needed-drone heuristic (favor fields that need few extra drones to reach full protection).
- Ensure at least half of the drones are protecting: first use idle/unassigned drones, filling available slots on high-threat fields; as a last resort, reassign protecting drones from non-primary fields but only if that doesn't drop those fields below full protection.
- Never overprotect a field; trim excess protectors by keeping the best-suited drones.
- Persist previous assignments per drone to bias future decisions (improves stability).

Below is a single Python implementation that follows these rules and calls environment.assign_group for every drone.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved SmartFarm adaptation:
    - Fully protect the most threatened field using closest/committed drones.
    - Prefer stability by favoring drones already protecting/moving to a field or previously assigned by this controller.
    - Try to fully protect additional fields prioritized by threat-per-needed-drone.
    - Ensure at least half of drones are protecting when possible.
    - Never overprotect fields; trim excess keepers by suitability.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # remember previous assignments for stability bias
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        # fallback idle group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # no threats -> idle all
            for c in components:
                environment.assign_group(c, idle_group)
                self.prev_assignments[id(c)] = idle_group
            return

        centers = {f.id: center(f) for f in threatened}
        fields_by_id = {f.id: f for f in threatened}

        # choose primary field: highest threat (tie-breaker fewer required drones)
        threatened.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = threatened[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil half

        # observed protecting drones by state
        observed_protecting = {f.id: 0 for f in threatened}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in observed_protecting:
                    observed_protecting[tid] += 1

        # helper: group name for a field (fallback idle)
        def protect_group(field):
            g = f"protecting {field.id}"
            return g if g in group_ids else idle_group

        # selection priority for a drone w.r.t. a field
        def select_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            prev = self.prev_assignments.get(id(drone))
            dist = distance(drone, centers[field.id])
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
            return (rank, prev_bonus, dist)

        assignments = {}
        unassigned = set(components)

        # 1) Fill primary field first (up to cap)
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, primary))
            chosen = candidates[:primary_cap]
            for d in chosen:
                assignments[d] = protect_group(primary)
                unassigned.discard(d)

        # 2) Try to fully protect additional fields prioritized by threat-per-needed-drone
        # baseline: observed + already assigned
        baseline = {}
        for f in threatened:
            grp = protect_group(f)
            assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
            obs = observed_protecting.get(f.id, 0)
            baseline[f.id] = assigned_now + obs

        field_list = []
        for f in threatened:
            if f.id == primary.id:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            already = baseline.get(f.id, 0)
            need = max(0, cap - already)
            score = f.threat_level / (need if need > 0 else 1e-6)
            field_list.append((score, -need, need, f))
        field_list.sort(reverse=True)

        for score, negneed, need, f in field_list:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            sel = sorted(list(unassigned), key=lambda d: select_key(d, f))[:need]
            for d in sel:
                assignments[d] = protect_group(f)
                unassigned.discard(d)

        # helper to count protecting drones (assigned + observed not in assignments)
        def count_protecting(assign_map):
            assigned_prot = sum(1 for g in assign_map.values() if isinstance(g, str) and g.startswith("protecting "))
            observed_extra = 0
            for c in components:
                if c in assign_map:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) in fields_by_id:
                    observed_extra += 1
            return assigned_prot + observed_extra

        # 3) Ensure at least half protecting: use unassigned first, then as last resort steal safely
        prot_count = count_protecting(assignments)
        if prot_count < min_protectors:
            need_more = min_protectors - prot_count
            # fill with unassigned to highest-threat fields with available capacity
            fields_by_threat = sorted(threatened, key=lambda f: f.threat_level, reverse=True)
            for f in fields_by_threat:
                if need_more <= 0 or not unassigned:
                    break
                grp = protect_group(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                obs = observed_protecting.get(f.id, 0)
                current_total = assigned_now + obs
                free_slots = max(0, cap - current_total)
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                chosen = sorted(list(unassigned), key=lambda d: select_key(d, f))[:take]
                for d in chosen:
                    assignments[d] = grp
                    unassigned.discard(d)
                    need_more -= 1

            # last resort: steal from protecting drones of non-primary fields if it doesn't drop those fields below cap
            if need_more > 0:
                steal_candidates = []
                for c in components:
                    if getattr(c, "state", None) != "protecting":
                        continue
                    tid = getattr(c, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    f = fields_by_id.get(tid)
                    if not f:
                        continue
                    # prefer stealing from low-threat fields and from drones farthest from their field
                    pen = (f.threat_level, -distance(c, centers[tid]))  # sort ascending by threat, then descending distance
                    steal_candidates.append((pen, c, f))
                steal_candidates.sort(key=lambda x: (x[0][0], x[0][1]))
                for _, c, f in steal_candidates:
                    if need_more <= 0:
                        break
                    grp_from = protect_group(f)
                    # compute total current protectors for this field (assigned + observed)
                    total_current = sum(1 for comp in components if (getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == f.id) or (assignments.get(comp) == grp_from))
                    cap_from = getattr(f, "drones_for_full_protection", 0)
                    # safe to steal if after removing this one there are still >= cap
                    if total_current - 1 >= cap_from:
                        assignments[c] = protect_group(primary)
                        # remove from unassigned if present
                        unassigned.discard(c)
                        need_more -= 1

        # 4) Keep unassigned drones on their current target if that field has free capacity (reduce churn)
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid and tid in fields_by_id:
                f = fields_by_id[tid]
                grp = protect_group(f)
                if grp in group_ids:
                    cap = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    obs = observed_protecting.get(f.id, 0)
                    if assigned_now + obs < cap:
                        assignments[d] = grp
                        unassigned.discard(d)

        # remaining unassigned -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.discard(d)

        # 5) Enforce caps: trim overprotection for each field by keeping best drones
        for f in threatened:
            grp = protect_group(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            # sort by suitability (select_key) and keep best cap
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 6) Apply assignments and record previous assignment for stability bias
        for c in components:
            grp = assignments.get(c, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(c, grp)
            self.prev_assignments[id(c)] = grp