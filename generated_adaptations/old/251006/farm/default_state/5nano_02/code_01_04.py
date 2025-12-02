from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance from drone to a point
        def dist_to_point(drone, point):
            lx = getattr(drone.location, "x", drone.location.x if hasattr(drone.location, "x") else 0.0)
            ly = getattr(drone.location, "y", drone.location.y if hasattr(drone.location, "y") else 0.0)
            return math.hypot(lx - point[0], ly - point[1])

        # Gather threat fields (threat_level > 0) sorted by threat level desc
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        assign_map = {}  # drone -> group_id string (single assignment)

        # If there is at least one threatening field, focus on the top one first
        if threat_fields:
            top_field = threat_fields[0]
            top_group = f"protecting {top_field.id}"
            # Current drones protecting the top field
            current_top = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id]
            for d in current_top:
                assign_map[d] = top_group  # explicit re-assign to same group

            required = int(getattr(top_field, "drones_for_full_protection", 0))
            needed = max(0, required - len(current_top))

            if needed > 0:
                center = field_center(top_field)
                candidates = [d for d in components if d not in assign_map]
                candidates.sort(key=lambda d: dist_to_point(d, center))

                for cand in candidates[:needed]:
                    assign_map[cand] = top_group

        # For other threat fields, try to fill to full protection with remaining drones
        remaining_fields = threat_fields[1:] if len(threat_fields) > 1 else []

        for f in remaining_fields:
            group = f"protecting {f.id}"
            # Ensure currently protecting drones for this field are assigned to the correct group
            current_for_field = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == f.id]
            for d in current_for_field:
                assign_map.setdefault(d, group)

            # Count current protection for this field (both from assign_map and actual state)
            current_assigned = len([d for d in components if assign_map.get(d) == group])
            current_actual = len(current_for_field)
            current_count = current_assigned + current_actual - current_assigned  # avoids double-counting
            # The above line simplifies to current_actual + 0 if no overlap; keep explicit:
            current_count = current_actual + current_assigned

            required = int(getattr(f, "drones_for_full_protection", 0))
            needed = max(0, required - current_count)

            if needed > 0:
                center = field_center(f)
                candidates = [d for d in components if d not in assign_map]
                candidates.sort(key=lambda d: dist_to_point(d, center))

                for cand in candidates[:needed]:
                    assign_map[cand] = group

        # Any drone not assigned yet should be idle
        for d in components:
            if d not in assign_map:
                assign_map[d] = "idle"

        # Apply assignments (exactly once per drone)
        for d, grp in assign_map.items():
            environment.assign_group(d, grp)