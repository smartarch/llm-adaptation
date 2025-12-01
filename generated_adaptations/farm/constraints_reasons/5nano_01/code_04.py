from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous group assignment per drone (by id)
        self._prev_groups = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threat fields
        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper: compute field center
        def center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: distance from drone to field center
        def dist_to_field(drone, field):
            cx, cy = center(field)
            x = getattr(drone.location, "x", 0.0)
            y = getattr(drone.location, "y", 0.0)
            dx = x - cx
            dy = y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Build mapping: field_id -> group_id
        field_group = {}
        for f in threat_fields:
            field_group[f.id] = f"protecting {f.id}"

        # If no threat, idle all
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._prev_groups[id(d)] = "idle"
            return

        # Sort threat fields by threat level descending
        threat_fields_sorted = sorted(threat_fields, key=lambda ff: ff.threat_level, reverse=True)
        most_threat_field = threat_fields_sorted[0]
        most_group = field_group[most_threat_field.id]
        capacity = getattr(most_threat_field, "drones_for_full_protection", 0)

        final_plan = {}

        # Step 1: Forcefully assign the closest drones to the most threatened field
        # Compute distances for all drones to the most threatened field center
        all_drones = list(components)
        dists_all = [(d, dist_to_field(d, most_threat_field)) for d in all_drones]
        dists_all.sort(key=lambda x: x[1])
        chosen_for_most = [d for d, _ in dists_all[:min(capacity, len(dists_all))]]

        for d in chosen_for_most:
            final_plan[d] = most_group
            self._prev_groups[id(d)] = most_group

        # Step 2: handle secondary fields with remaining drones
        remaining_drones = [d for d in components if d not in chosen_for_most]

        for f in threat_fields_sorted[1:]:
            gid = field_group[f.id]
            cap = getattr(f, "drones_for_full_protection", 0)
            current = [d for d in remaining_drones if self._prev_groups.get(id(d)) == gid]
            cur_f = len(current)

            if cur_f > cap:
                # Over-protected: move farthest away
                dists = [(d, dist_to_field(d, f)) for d in current]
                dists.sort(key=lambda x: x[1], reverse=True)
                over = cur_f - cap
                for i in range(over):
                    d, _ = dists[i]
                    final_plan[d] = "idle"
                    self._prev_groups.pop(id(d), None)
                current = [d for d in remaining_drones if self._prev_groups.get(id(d)) == gid]
                cur_f = len(current)

            if cur_f < cap:
                need = cap - cur_f
                # candidates from remaining_drones that are not already assigned to gid
                candidates = [d for d in remaining_drones if self._prev_groups.get(id(d)) != gid]
                candidates.sort(key=lambda d: dist_to_field(d, f))
                for i in range(min(need, len(candidates))):
                    d = candidates[i]
                    final_plan[d] = gid
                    self._prev_groups[id(d)] = gid

        # Step 3: enforce at least half protection
        total = len(components)
        protecting_now = [d for d in components if self._prev_groups.get(id(d)) in field_group.values()]
        if len(protecting_now) < (total / 2.0):
            needed = int((total / 2.0) - len(protecting_now))
            free = [d for d in components if self._prev_groups.get(id(d)) not in field_group.values()]
            for f in threat_fields_sorted:
                if needed <= 0:
                    break
                gid = field_group[f.id]
                current_f = [d for d in components if self._prev_groups.get(id(d)) == gid]
                cap = getattr(f, "drones_for_full_protection", 0)
                if len(current_f) >= cap:
                    continue
                to_allocate = cap - len(current_f)
                free.sort(key=lambda d: dist_to_field(d, f))
                take = min(to_allocate, len(free), needed)
                for i in range(take):
                    d = free[i]
                    final_plan[d] = gid
                    self._prev_groups[id(d)] = gid
                needed -= take
                free = free[take:]

        # Finalize: ensure all drones have a valid group in group_ids
        for d in components:
            if d in final_plan:
                gid = final_plan[d]
            else:
                prev = self._prev_groups.get(id(d))
                gid = prev if prev is not None else "idle"
            if gid not in group_ids:
                gid = "idle"
            final_plan[d] = gid
            self._prev_groups[id(d)] = gid

        # Apply the group assignments
        for d, gid in final_plan.items():
            environment.assign_group(d, gid)