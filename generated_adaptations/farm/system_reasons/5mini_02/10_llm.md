Reasoning and adaptation strategy

Improvements over the previous version
- Stronger stability: prefer drones already protecting or moving to a field, and prefer drones we previously assigned to the same protecting group (we store previous assignments) to reduce churn.
- Better field selection: after securing the top-threat field, try to fully protect other fields prioritized by threat-per-needed-drone (more full protections is better than many partial ones).
- Ensure at least half of drones are protecting: first use idle/unassigned drones; only as a last resort steal protecting drones from non-primary fields that are least critical (low threat and far away).
- Never overprotect: enforce each field's drones_for_full_protection cap.
- Always call environment.assign_group for every drone and fall back to "idle" group if a protecting group name is missing.

The code below implements this strategy.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved SmartFarm adaptation focusing on:
    - Always fully protecting the most threatened field with closest/committed drones.
    - Prioritizing full protections of additional fields by threat-per-needed-drone.
    - Maintaining stability by preferring previously assigned drones and those already protecting/moving to a field.
    - Ensuring at least half the drones are protecting when possible.
    - Never overprotecting fields.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # store previous assignments by component id to bias stability
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        # idle fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Collect threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threat => idle all drones
            for c in components:
                environment.assign_group(c, idle_group)
                self.prev_assignments[id(c)] = idle_group
            return

        # Prepare lookups
        centers = {f.id: center(f) for f in threatened}
        fields_by_id = {f.id: f for f in threatened}

        # Choose primary: highest threat (tie-breaker fewer required drones)
        threatened.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = threatened[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil half

        # Observed protecting drones (state == "protecting") per field id
        observed_protectors = {f.id: 0 for f in threatened}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in observed_protectors:
                    observed_protectors[tid] += 1

        # Priority key for selecting drones for a field
        def select_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            prev = self.prev_assignments.get(id(drone))
            # Preference ordering
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
            return (rank, prev_bonus, dist(drone, centers[field.id]))

        # assignment structures
        assignments = {}
        unassigned = set(components)

        # helper for group name (fallback to idle_group)
        def protect_group(field):
            g = f"protecting {field.id}"
            return g if g in group_ids else idle_group

        # 1) Assign primary field fully using best candidates
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, primary))
            chosen = candidates[:primary_cap]
            for d in chosen:
                assignments[d] = protect_group(primary)
                unassigned.discard(d)

        # 2) Attempt to fully protect other fields prioritized by threat-per-needed-drone
        # baseline: observed protecting + already assigned for each field
        baseline = {}
        for f in threatened:
            grp = protect_group(f)
            assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
            obs = observed_protectors.get(f.id, 0)
            baseline[f.id] = assigned_now + obs

        # build candidate list
        candidates = []
        for f in threatened:
            if f.id == primary.id:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            already = baseline.get(f.id, 0)
            need = max(0, cap - already)
            score = f.threat_level / (need if need > 0 else 1e-6)
            candidates.append((score, -need, need, f))
        candidates.sort(reverse=True)

        for score, negneed, need, f in candidates:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            sel = sorted(list(unassigned), key=lambda d: select_key(d, f))[:need]
            for d in sel:
                assignments[d] = protect_group(f)
                unassigned.discard(d)

        # 3) Ensure at least half are protecting (use unassigned first, then as last resort steal)
        def count_protecting(assign_map):
            assigned_prot = sum(1 for g in assign_map.values() if isinstance(g, str) and g.startswith("protecting "))
            observed_extra = 0
            for c in components:
                if c in assign_map:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) in fields_by_id:
                    observed_extra += 1
            return assigned_prot + observed_extra

        prot_count = count_protecting(assignments)
        if prot_count < min_protectors:
            need_more = min_protectors - prot_count
            # fill with unassigned: assign to highest-threat fields with available capacity first
            fields_by_threat = sorted(threatened, key=lambda f: f.threat_level, reverse=True)
            for f in fields_by_threat:
                if need_more <= 0 or not unassigned:
                    break
                grp = protect_group(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                obs = observed_protectors.get(f.id, 0)
                current_total = assigned_now + obs
                free_slots = max(0, cap - current_total)
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                sel = sorted(list(unassigned), key=lambda d: select_key(d, f))[:take]
                for d in sel:
                    assignments[d] = grp
                    unassigned.discard(d)
                    need_more -= 1

            # last resort: steal from protecting drones of non-primary fields (least critical ones)
            if need_more > 0:
                stealables = []
                for c in components:
                    if getattr(c, "state", None) != "protecting":
                        continue
                    tid = getattr(c, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    f = fields_by_id.get(tid)
                    if not f:
                        continue
                    # prefer stealing from low-threat and far drones
                    score = (f.threat_level, dist(c, centers[tid]))
                    stealables.append((score, c, f))
                # sort by low threat then far distance
                stealables.sort(key=lambda x: (x[0][0], -x[0][1]))
                for _, c, f in stealables:
                    if need_more <= 0:
                        break
                    grp_from = protect_group(f)
                    cap_from = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp_from)
                    observed = sum(1 for comp in components if comp not in assignments and getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == f.id and comp is not c)
                    total_if_removed = assigned_now + observed
                    if total_if_removed >= cap_from:
                        # safe to steal
                        assignments[c] = protect_group(primary)
                        if c in unassigned:
                            unassigned.discard(c)
                        need_more -= 1

        # 4) Keep unassigned drones on their current target if it helps (reduces churn)
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid and tid in fields_by_id:
                grp = protect_group(fields_by_id[tid])
                if grp in group_ids:
                    f = fields_by_id[tid]
                    cap = getattr(f, "drones_for_full_protection", 0)
                    assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                    obs = observed_protectors.get(f.id, 0)
                    if assigned_now + obs < cap:
                        assignments[d] = grp
                        unassigned.discard(d)

        # Remaining unassigned -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.discard(d)

        # 5) Enforce caps: trim any overprotection, keep best candidates by select_key
        for f in threatened:
            grp = protect_group(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            # keep best cap drones
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep_set = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 6) Apply assignments and record prev_assignments
        for c in components:
            grp = assignments.get(c, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(c, grp)
            self.prev_assignments[id(c)] = grp