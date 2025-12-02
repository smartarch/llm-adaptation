import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields (threat_level > 0)
        threatened_fields = []
        for field in environment.fields:
            tl = getattr(field, "threat_level", 0)
            if tl is None:
                tl = 0
            if tl > 0:
                threatened_fields.append(field)

        # If no threats, explicitly idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Process threatened fields in order of highest threat level
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        allocated = set()

        for field in threatened_fields:
            drones_for_full = int(getattr(field, "drones_for_full_protection", 0))
            protecting_now = int(getattr(field, "protecting_drones", 0))
            arriving_now = int(getattr(field, "arriving_drones", 0))

            # How many more drones are needed to reach full protection
            needed = max(0, drones_for_full - (protecting_now + arriving_now))
            if needed <= 0:
                continue

            target_group = f"protecting {field.id}"
            if target_group not in group_ids:
                continue

            # Build candidate drones not yet allocated
            candidates = [d for d in components if d not in allocated]

            # Center of the field for distance computation
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0

            def dist_to_field(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                return math.hypot(loc.x - cx, loc.y - cy)

            candidates.sort(key=dist_to_field)

            take = min(needed, len(candidates))
            for i in range(take):
                d = candidates[i]
                allocated.add(d)
                environment.assign_group(d, target_group)

        # Explicitly assign any remaining drones to idle (to satisfy the "every component must be assigned" rule)
        for d in components:
            if d not in allocated:
                environment.assign_group(d, "idle")