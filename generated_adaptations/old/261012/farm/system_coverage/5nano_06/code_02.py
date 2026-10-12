from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Identify the field with the highest threat
        top_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        top_group = f"protecting {top_field.id}"

        # Compute how many drones are currently protecting the top field
        currently_protecting = [
            d for d in components
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        current_count = len(currently_protecting)

        # How many drones are needed for full protection
        needed = int(getattr(top_field, "drones_for_full_protection", 0))
        if needed < 0:
            needed = 0

        # Determine drones to add to top_field (closest to field center)
        drones_for_top = list(currently_protecting)

        if current_count < needed:
            # Compute field center
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Candidates: drones not currently protecting the top field
            candidates = [
                d for d in components
                if not (getattr(d, "state", "idle") == "protecting" and getattr(d, "target_id", None) == top_field.id)
            ]

            def distance_to_field(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                x = getattr(loc, "x", 0.0)
                y = getattr(loc, "y", 0.0)
                return math.hypot(x - cx, y - cy)

            candidates.sort(key=distance_to_field)

            # Pick the closest until we reach the needed count
            for d in candidates:
                if len(drones_for_top) >= needed:
                    break
                drones_for_top.append(d)

        # Final set of drones that should be in the top field protection
        top_field_drones = set(drones_for_top)

        # Assign all drones to their final groups:
        for d in components:
            if d in top_field_drones:
                environment.assign_group(d, top_group)
            else:
                environment.assign_group(d, "idle")