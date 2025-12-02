import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened_fields = []
        for field in environment.fields:
            tl = getattr(field, "threat_level", 0)
            if tl is None:
                tl = 0
            if tl > 0:
                threatened_fields.append(field)

        # If no threats, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        allocated = set()

        for field in threatened_fields:
            drones_for_full = int(getattr(field, "drones_for_full_protection", 0))
            protecting_now = int(getattr(field, "protecting_drones", 0))
            arriving_now = int(getattr(field, "arriving_drones", 0))

            # Drones still arriving will contribute soon; compute need to reach full protection
            needed = max(0, drones_for_full - (protecting_now + arriving_now))

            if needed <= 0:
                # Field already effectively fully protected (considering arrivals)
                continue

            target_group = f"protecting {field.id}"
            if target_group not in group_ids:
                # If the group isn't valid, skip this field
                continue

            # Build candidate drones to allocate to this field
            candidates = [d for d in components if d not in allocated]

            # Exclude drones already protecting this exact field
            candidates = [
                d for d in candidates
                if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id)
            ]

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
                environment.assign_group(d, target_group)
                allocated.add(d)

        # After attempting to protect threatened fields, decide on remaining drones
        for d in components:
            if d in allocated:
                continue
            # Do not disturb drones currently protecting any field
            if getattr(d, "state", None) == "protecting":
                continue
            # Otherwise, idle the drone
            environment.assign_group(d, "idle")