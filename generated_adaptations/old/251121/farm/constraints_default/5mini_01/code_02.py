from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Ensure components is a list we can iterate multiple times
        drones = list(components)

        # Build list of fields with threat_level > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, send all drones to idle
        if not threatened_fields:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        # Select the field with the highest threat_level (tie-break by id for determinism)
        def field_key(f):
            return (f.threat_level, f.id)
        max_field = max(threatened_fields, key=field_key)

        # Compute field center for distance calculations
        center_x = (max_field.left + max_field.right) / 2.0
        center_y = (max_field.top + max_field.bottom) / 2.0

        # Helper: euclidean distance from drone to field center
        def dist_to_field(drone):
            dx = getattr(drone.location, "x", 0) - center_x
            dy = getattr(drone.location, "y", 0) - center_y
            return math.hypot(dx, dy)

        # Count drones currently protecting the max_field and keep them
        protecting_group_name = f"protecting {max_field.id}"
        required = int(getattr(max_field, "drones_for_full_protection", 0))

        currently_protecting = [
            d for d in drones
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == max_field.id
        ]

        # Assign all currently_protecting drones to the protecting group (explicit)
        for d in currently_protecting:
            environment.assign_group(d, protecting_group_name)

        num_current = len(currently_protecting)

        # If already fully protected (num_current >= required), keep these and set all others to idle
        if num_current >= required:
            for d in drones:
                if d in currently_protecting:
                    continue
                environment.assign_group(d, "idle")
            return

        # Need additional drones to reach required; consider all other drones sorted by distance
        remaining_needed = required - num_current

        # Build pool of candidate drones (exclude those already assigned above)
        candidates = [d for d in drones if d not in currently_protecting]

        # Sort candidates by distance ascending (closest first)
        candidates.sort(key=dist_to_field)

        # Select up to remaining_needed drones (if fewer available, select all)
        selected_additional = candidates[:remaining_needed]

        # Assign those selected additional drones to the protecting group
        for d in selected_additional:
            environment.assign_group(d, protecting_group_name)

        # Assign all other drones to idle (those not in currently_protecting and not in selected_additional)
        selected_set = set(selected_additional)
        current_set = set(currently_protecting)
        for d in drones:
            if d in current_set or d in selected_set:
                continue
            environment.assign_group(d, "idle")