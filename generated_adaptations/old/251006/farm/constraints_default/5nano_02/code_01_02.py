import math
import abc
from generated_adaptations.base_classes import farm as base_farm

class SmartFarmAdaptation(base_farm.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat level
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no field requires protection, idle all drones
        if not fields_with_threat:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Choose the field with the highest threat level
        target_field = max(fields_with_threat, key=lambda fld: getattr(fld, "threat_level", 0))
        protect_group = f"protecting {target_field.id}"

        # Determine how many drones are required for full protection
        required = getattr(target_field, "drones_for_full_protection", 0)
        if required is None:
            required = 0
        if required < 0:
            required = 0

        # Count currently protecting drones for the target field
        current_protecting = [
            c for c in components
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id
        ]
        protect_count = len(current_protecting)

        # If already fully protected, keep those and idle the rest
        if protect_count >= required:
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id:
                    environment.assign_group(c, protect_group)
                else:
                    environment.assign_group(c, "idle")
            return

        # Need additional drones to reach full protection
        extra_needed = max(0, int(required - protect_count))

        # Compute center of the field for distance calculation
        center_x = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        center_y = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Build candidate list: drones not currently protecting this field
        candidates = []
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id:
                continue
            loc = getattr(c, "location", None)
            if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                dist = float("inf")
            else:
                dist = math.hypot(loc.x - center_x, loc.y - center_y)
            candidates.append((dist, c))

        # Sort by distance (closest first)
        candidates.sort(key=lambda t: t[0])

        # Assign the closest extra_needed drones to protect the field
        allocated = 0
        for dist, c in candidates:
            if allocated >= extra_needed:
                break
            environment.assign_group(c, protect_group)
            allocated += 1

        # The remaining drones (including those not allocated or far away) go idle
        for dist, c in candidates[allocated:]:
            environment.assign_group(c, "idle")

        # Ensure any already-protecting drones for this field stay in the correct group
        for c in current_protecting:
            environment.assign_group(c, protect_group)