from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance from drone to a point
        def dist_to_point(drone, point):
            loc = getattr(drone, "location", None)
            if loc is None:
                dx = dy = 0.0
            else:
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
            return math.hypot(dx - point[0], dy - point[1])

        # Gather threat fields (threat_level > 0) sorted by threat level desc
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        assigned = {}  # drone -> group_id string (single assignment)

        # If there is at least one threatening field, focus on the top one first
        if threat_fields:
            top_field = threat_fields[0]
            top_group = f"protecting {top_field.id}"

            # Drones currently protecting top field
            current_top = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id
            ]
            # Drones moving toward top field
            moving_to_top = [
                d for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id
            ]

            # Ensure current and moving drones are assigned to top_group
            for d in current_top + moving_to_top:
                assigned[d] = top_group

            required = int(getattr(top_field, "drones_for_full_protection", 0))
            current_count = len(current_top) + len(moving_to_top)

            if current_count < required:
                needed = required - current_count
                center = field_center(top_field)
                # Candidates are those not already assigned
                candidates = [d for d in components if d not in assigned]
                candidates.sort(key=lambda d: dist_to_point(d, center))

                for cand in candidates[:needed]:
                    assigned[cand] = top_group

        # For other threat fields, try to fill to full protection with remaining drones
        remaining_fields = threat_fields[1:] if len(threat_fields) > 1 else []

        for f in remaining_fields:
            group = f"protecting {f.id}"
            # Drones currently protecting this field
            current_for_field = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == f.id
            ]
            # Drones moving toward this field
            moving_to_field = [
                d for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == f.id
            ]

            # Ensure current (protecting or moving) drones are assigned to this group
            for d in current_for_field + moving_to_field:
                assigned[d] = group

            current_count = len(current_for_field) + len(moving_to_field)

            required = int(getattr(f, "drones_for_full_protection", 0))
            if current_count < required:
                needed = required - current_count
                center = field_center(f)
                # Exclude drones already assigned
                candidates = [d for d in components if d not in assigned]
                candidates.sort(key=lambda d: dist_to_point(d, center))

                for cand in candidates[:needed]:
                    assigned[cand] = group

        # Any drone not assigned yet should be idle
        for d in components:
            if d not in assigned:
                assigned[d] = "idle"

        # Apply assignments (exactly once per drone)
        for d, grp in assigned.items():
            environment.assign_group(d, grp)