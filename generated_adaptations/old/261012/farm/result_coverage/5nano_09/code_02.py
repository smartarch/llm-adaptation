from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, send all drones to idle
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))

        # Determine the group name for protecting the top field
        protect_group = f"protecting {top_field.id}"
        if protect_group not in group_ids:
            protect_group = "idle"  # fallback if the group name is not valid

        # Compute how many drones currently protect the top field
        current_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        current_count = len(current_protecting)

        required_for_full = getattr(top_field, "drones_for_full_protection", 0)

        # If already fully protected, keep current protectors, others idle
        if current_count >= max(0, required_for_full):
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    environment.assign_group(d, protect_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Need additional drones to reach full protection
        needed = max(0, int(required_for_full) - current_count)
        if needed <= 0:
            # No additional drones needed, ensure current protectors are in correct group
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    environment.assign_group(d, protect_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Determine the center of the field
        left = getattr(top_field, "left", 0.0)
        right = getattr(top_field, "right", 0.0)
        top = getattr(top_field, "top", 0.0)
        bottom = getattr(top_field, "bottom", 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Sort drones by distance to the field center (squared distance to avoid sqrt)
        def dist_sq(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - center_x
            dy = getattr(loc, "y", 0.0) - center_y
            return dx * dx + dy * dy

        drones_sorted = sorted(components, key=dist_sq)

        # Pick the closest 'needed' drones
        chosen = set(drones_sorted[:needed])

        # Assign groups
        for d in components:
            if d in chosen:
                # Ensure the protect group exists in group_ids
                if protect_group in group_ids:
                    environment.assign_group(d, protect_group)
                else:
                    environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, "idle")