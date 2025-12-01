from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous group assignment per drone (by id)
        # Key: id(drone) -> group_name
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
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
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

        # Initialize final plan and update memory
        final_plan = {}

        # Count how many drones are currently assigned to most_threat_field
        current_on_most = [
            d for d in components if self._prev_groups.get(id(d)) == most_group
        ]
        cur = len(current_on_most)

        # If over-protected, move the farthest drones away
        if cur > capacity:
            # Distances to the most threatened field
            dists = [(d, dist_to_field(d, most_threat_field)) for d in current_on_most]
            dists.sort(key=lambda x: x[1], reverse=True)  # farthest first
            over = cur - capacity
            for i in range(over):
                d, _ = dists[i]
                final_plan[d] = "idle"
                # Clear memory for this drone
                self._prev_groups.pop(id(d), None)
            # Recompute the current set
            current_on_most = [
                d for d in components if self._prev_groups.get(id(d)) == most_group
            ]
            cur = len(current_on_most)

        # If under-protected, assign nearest drones to most threatened field
        if cur < capacity:
            need = capacity - cur
            candidates = [d for d in components if self._prev_groups.get(id(d)) != most_group]
            candidates.sort(key=lambda d: dist_to_field(d, most_threat_field))
            for i in range(min(need, len(candidates))):
                d = candidates[i]
                final_plan[d] = most_group
                self._prev_groups[id(d)] = most_group
            cur = len([d for d in components if self._prev_groups.get(id(d)) == most_group])

        # Now handle other threat fields (secondary protection)
        for f in threat_fields_sorted[1:]:
            gid = field_group[f.id]
            cap = getattr(f, "drones_for_full_protection", 0)
            current = [d for d in components if self._prev_groups.get(id(d)) == gid]
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
                current = [d for d in components if self._prev_groups.get(id(d)) == gid]
                cur_f = len(current)

            if cur_f < cap:
                need = cap - cur_f
                candidates = [d for d in components if self._prev_groups.get(id(d)) != gid]
                candidates.sort(key=lambda d: dist_to_field(d, f))
                for i in range(min(need, len(candidates))):
                    d = candidates[i]
                    final_plan[d] = gid
                    self._prev_groups[id(d)] = gid

        # Ensure at least half of the drones are protecting (approximate stability)
        total_drones = len(components)
        protecting_now = [
            d for d in components if self._prev_groups.get(id(d)) in field_group.values()
        ]
        if len(protecting_now) < (total_drones / 2.0):
            needed = int((total_drones / 2.0) - len(protecting_now))
            # Drones not currently protecting anyone
            free = [d for d in components if self._prev_groups.get(id(d)) not in field_group.values()]
            # Allocate to threat fields in order of threat
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

        # Finalize: any drone not in final_plan should be idle or follow previous group if valid
        for d in components:
            if d in final_plan:
                gid = final_plan[d]
            else:
                prev = self._prev_groups.get(id(d))
                if prev is None:
                    gid = "idle"
                else:
                    gid = prev
            if gid not in group_ids:
                gid = "idle"
            final_plan[d] = gid
            self._prev_groups[id(d)] = gid

        # Apply the group assignments
        for d, gid in final_plan.items():
            environment.assign_group(d, gid)