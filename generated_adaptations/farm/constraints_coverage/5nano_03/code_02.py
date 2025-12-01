import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level (>0)
        top_field = None
        max_threat = -1.0
        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > 0:
                if field.threat_level > max_threat:
                    max_threat = field.threat_level
                    top_field = field

        # If there is no threatened field, idle all drones
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Count how many drones are currently protecting the top field
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protecting += 1

        # How many drones are required for full protection of the top field
        required = getattr(top_field, "drones_for_full_protection", 0)
        if required <= 0:
            # If no protection is defined, idle all
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Drones we still need to assign to top_field
        to_assign_now = max(0, int(required) - int(current_protecting))

        # Helper to compute distance from a drone to the top field center
        def distance_to_field(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Collect available drones not currently protecting the top field
        available = []
        for d in components:
            if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id):
                dist = distance_to_field(d, top_field)
                available.append((dist, d))
        available.sort(key=lambda t: t[0])

        # Choose the closest drones to fill the gap
        chosen = set()
        for _, d in available[:to_assign_now]:
            chosen.add(d)

        top_group = f"protecting {top_field.id}"

        # Reassign groups for all drones
        for d in components:
            if (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id) or (d in chosen):
                environment.assign_group(d, top_group)
            else:
                environment.assign_group(d, "idle")

    # (Optional) Helper retained only if needed elsewhere
    def _distance_to_field(self, drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = getattr(drone.location, "x", 0.0) - cx
        dy = getattr(drone.location, "y", 0.0) - cy
        return math.hypot(dx, dy)