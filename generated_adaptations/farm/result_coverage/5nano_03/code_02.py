import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Identify top-threat field (threat_level > 0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(fields, key=lambda f: getattr(f, "threat_level", 0))
        top_field_id = top_field.id

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        top_center = field_center(top_field)
        # Helper to compute distance from drone to field center
        def dist_to_field(drone, center):
            dx = getattr(drone.location, "x", 0.0) - center[0]
            dy = getattr(drone.location, "y", 0.0) - center[1]
            return math.hypot(dx, dy)

        # Step 2: Determine how many drones are currently protecting the top field
        currently_protecting = []
        other_drones = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                currently_protecting.append(d)
            else:
                other_drones.append(d)

        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Step 3 & 4: Ensure exactly 'needed' drones are protecting top_field using closest ones
        assigned_to_top = []

        # Start with currently protecting drones (they'll remain if needed)
        if len(currently_protecting) > 0:
            # If we need fewer than currently protecting, trim extras
            if len(currently_protecting) >= needed:
                assigned_to_top = currently_protecting[:needed]
            else:
                assigned_to_top = list(currently_protecting)

        # If we still need more drones to reach 'needed', pick from the pool of available drones
        if len(assigned_to_top) < needed:
            # Pool: all drones not currently protecting top_field
            pool = [d for d in components if d not in assigned_to_top and not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id)]
            # Sort pool by distance to top_field center (closest first)
            pool.sort(key=lambda d: dist_to_field(d, top_center))
            needed_more = needed - len(assigned_to_top)
            assigned_to_top.extend(pool[:needed_more])

        # Step 5: Assign groups
        # First, assign the selected drones to protecting top_field
        for d in assigned_to_top:
            environment.assign_group(d, f"protecting {top_field_id}")

        # Step 6: Assign all remaining drones to idle
        for d in components:
            if d not in assigned_to_top:
                environment.assign_group(d, "idle")