from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy to protect fields:
    - Fully protect the highest-threat field using closest/committed drones.
    - Favor stability by preferring existing protectors, movers, and previously assigned drones.
    - Try to fully protect additional fields by threat-per-needed-drone heuristic.
    - Ensure at least half of drones are protecting when possible.
    - Never overprotect fields.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, ctr):
            dx = drone.location.x - ctr[0]
            dy = drone.location.y - ctr[1]
            return math.hypot(dx, dy)

        # Idle fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Threatened fields (>0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, idle_group)
                self.prev_assignments[id(c)] = idle_group
            return

        # Precompute centers and lookup
        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        # Primary field: highest threat, tie-breaker smaller required drones (faster to secure)
        fields.sort(key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary = fields[0]

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil half

        # Observed protecting counts from drone states
        observed_protecting = {f.id: 0 for f in fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in observed_protecting:
                    observed_protecting[tid] += 1

        # Protecting group name helper
        def protect_group(f):
            g = f"protecting {f.id}"
            return g if g in group_ids else idle_group

        # Priority key for selecting drones to allocate to a field
        def select_key(d, f):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            prev = self.prev_assignments.get(id(d))
            distance = dist(d, centers[f.id])
            if st == "protecting" and tid == f.id:
                rank = 0
            elif st == "moving_to_field" and tid == f.id:
                rank = 1
            elif prev == f"protecting {f.id}":
                rank = 2
            elif st == "idle":
                rank = 3
            elif st == "moving_to_field":
                rank = 4
            elif st == "protecting":
                rank = 5
            else:
                rank = 6
            prev_bonus = 0 if prev == f"protecting {f.id}" else 1
            return (rank, prev_bonus, distance)

        # Start assignments
        assignments = {}
        unassigned = set(components)

        # 1) Secure primary field (up to cap)
        primary_cap = getattr(primary, "drones_for_full_protection", 0)
        if primary_cap > 0:
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, primary))
            for d in candidates[:primary_cap]:
                assignments[d] = protect_group(primary)
                unassigned.discard(d)

        # 2) Try to fully protect additional fields by threat-per-needed-drone
        # baseline = observed protecting + already assigned
        baseline = {}
        for f in fields:
            grp = protect_group(f)
            assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
            baseline[f.id] = assigned_now + observed_protecting.get(f.id, 0)

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
            field_candidates.append((score, -need, need, f))
        field_candidates.sort(reverse=True)

        for _, _, need, f in field_candidates:
            if need <= 0:
                continue
            if len(unassigned) < need:
                continue
            picked = sorted(list(unassigned), key=lambda d: select_key(d, f))[:need]
            for d in picked:
                assignments[d] = protect_group(f)
                unassigned.discard(d)

        # Helper: count protecting (assigned + observed not assigned)
        def count_protecting(assigns):
            assigned_prot = sum(1 for g in assigns.values() if isinstance(g, str) and g.startswith("protecting "))
            observed_extra = 0
            for d in components:
                if d in assigns:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fields_by_id:
                    observed_extra += 1
            return assigned_prot + observed_extra

        # 3) Ensure at least half protecting: fill with unassigned first, then steal if absolutely necessary
        prot_count = count_protecting(assignments)
        if prot_count < min_protectors:
            need_more = min_protectors - prot_count
            # Use unassigned to fill high-threat fields with free slots first
            for f in sorted(fields, key=lambda x: x.threat_level, reverse=True):
                if need_more <= 0 or not unassigned:
                    break
                grp = protect_group(f)
                cap = getattr(f, "drones_for_full_protection", 0)
                assigned_now = sum(1 for comp, g in assignments.items() if g == grp)
                observed = observed_protecting.get(f.id, 0)
                free_slots = max(0, cap - (assigned_now + observed))
                take = min(len(unassigned), need_more, free_slots if free_slots > 0 else len(unassigned))
                if take <= 0:
                    continue
                pick = sorted(list(unassigned), key=lambda d: select_key(d, f))[:take]
                for d in pick:
                    assignments[d] = grp
                    unassigned.discard(d)
                    need_more -= 1

            # Last resort: steal from protecting drones of non-primary fields if safe
            if need_more > 0:
                steal_list = []
                for d in components:
                    if getattr(d, "state", None) != "protecting":
                        continue
                    tid = getattr(d, "target_id", None)
                    if not tid or tid == primary.id:
                        continue
                    f = fields_by_id.get(tid)
                    if not f:
                        continue
                    # prefer stealing from lower-threat and drones farther away
                    penalty = (f.threat_level, -dist(d, centers[tid]))
                    steal_list.append((penalty, d, f))
                steal_list.sort(key=lambda x: (x[0][0], x[0][1]))
                for _, d, f in steal_list:
                    if need_more <= 0:
                        break
                    grp_from = protect_group(f)
                    total_current = sum(1 for comp in components if ((getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == f.id) or (assignments.get(comp) == grp_from)))
                    cap_from = getattr(f, "drones_for_full_protection", 0)
                    if total_current - 1 >= cap_from:
                        assignments[d] = protect_group(primary)
                        unassigned.discard(d)
                        need_more -= 1

        # 4) Keep unassigned drones on their current target if that target has capacity (reduces churn)
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

        # 6) Enforce caps: trim any protecting group above cap by keeping best-suited drones
        for f in fields:
            grp = protect_group(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = [d for d, g in assignments.items() if g == grp]
            if len(assigned_list) <= cap:
                continue
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 7) Apply assignments and persist for stability
        for c in components:
            grp = assignments.get(c, idle_group)
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(c, grp)
            self.prev_assignments[id(c)] = grp