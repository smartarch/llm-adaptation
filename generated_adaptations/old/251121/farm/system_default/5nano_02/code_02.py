import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level (> 0)
        target_field = None
        max_threat = -1.0
        for f in environment.fields:
            th = getattr(f, "threat_level", 0.0)
            if th > 0.0 and th > max_threat:
                max_threat = th
                target_field = f

        # If no field needs protection, send all drones to idle
        if target_field is None:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        field_id = target_field.id
        group_name = f"protecting {field_id}"
        # Determine how many drones are required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))
        if required < 0:
            required = 0

        # Count how many drones are currently protecting this field
        current_protecting_indices = []
        for idx, drone in enumerate(components):
            if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) == field_id:
                current_protecting_indices.append(idx)

        current_protecting_count = len(current_protecting_indices)

        # If protection is not required, assign all to idle
        if required == 0 or current_protecting_count >= required:
            protected_set = set(current_protecting_indices)
        else:
            need = required - current_protecting_count
            # Compute field center
            center_x = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
            center_y = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

            # Prepare distances for candidates not currently protecting this field
            candidates = []
            for idx, drone in enumerate(components):
                if idx in current_protecting_indices:
                    continue
                loc = getattr(drone, "location", None)
                if loc is None:
                    dist_sq = float("inf")
                else:
                    dx = loc.x - center_x
                    dy = loc.y - center_y
                    dist_sq = dx * dx + dy * dy
                candidates.append((dist_sq, idx))

            candidates.sort()
            selected_indices = [idx for _, idx in candidates[:need]]
            protected_set = set(current_protecting_indices)
            protected_set.update(selected_indices)

        # Assign groups: protected drones to the protecting field group, others to idle
        for i, drone in enumerate(components):
            if i in protected_set:
                environment.assign_group(drone, group_name)
            else:
                environment.assign_group(drone, "idle")