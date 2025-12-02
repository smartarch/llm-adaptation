import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level (> 0)
        highest_field = None
        max_threat = -1.0
        for f in getattr(environment, "fields", []) or []:
            threat = getattr(f, "threat_level", 0.0)
            if threat > 0.0 and threat > max_threat:
                max_threat = threat
                highest_field = f

        # If there is no threatened field, idle all drones
        if highest_field is None:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Target group for the highest threat field
        target_group = f"protecting {highest_field.id}"

        # Determine how many drones are currently protecting this field
        assigned_to_target = set()
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == highest_field.id:
                environment.assign_group(c, target_group)
                assigned_to_target.add(c)

        current_protecting = len(assigned_to_target)

        # If we need more drones to reach full protection
        required = getattr(highest_field, "drones_for_full_protection", 0)

        if current_protecting < required:
            # Compute field center
            cx = (highest_field.left + highest_field.right) / 2.0
            cy = (highest_field.top + highest_field.bottom) / 2.0

            # Prepare candidates (not already protecting this field)
            candidates = [d for d in components if d not in assigned_to_target]

            def distance_to_field(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return (dx * dx + dy * dy) ** 0.5

            candidates.sort(key=distance_to_field)

            need = min(required - current_protecting, len(candidates))
            for i in range(need):
                environment.assign_group(candidates[i], target_group)
                assigned_to_target.add(candidates[i])

        # Re-assign all drones not assigned to the highest-field protection to idle
        for c in components:
            if c not in assigned_to_target:
                environment.assign_group(c, "idle")