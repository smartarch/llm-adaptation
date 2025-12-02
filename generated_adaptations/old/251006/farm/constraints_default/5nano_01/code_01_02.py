import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the top-threat field
        top_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        top_group = f"protecting {top_field.id}"

        # Compute center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # How many drones are required for full protection
        required = getattr(top_field, "drones_for_full_protection", 0)

        # Drones currently protecting the top field
        currently_protecting_top = [
            d for d in components if d.state == "protecting" and d.target_id == top_field.id
        ]
        currently_protecting_count = len(currently_protecting_top)

        # If we need more drones to reach full protection, select closest candidates
        if currently_protecting_count < required:
            # Build candidate pool: those not already protecting the top field
            candidates = []
            for d in components:
                if d in currently_protecting_top:
                    continue
                if d.state == "protecting" and d.target_id is not None:
                    # This drone is protecting some other field; skip reassigning to avoid disrupting it
                    continue
                # Compute distance to the top field center
                if getattr(d, "location", None) is not None:
                    dx = d.location.x - cx
                    dy = d.location.y - cy
                    dist = math.hypot(dx, dy)
                else:
                    dist = float("inf")
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])
            needed = required - currently_protecting_count
            for i in range(min(needed, len(candidates))):
                _, drone = candidates[i]
                environment.assign_group(drone, top_group)
                currently_protecting_top.append(drone)

        # Final step: ensure every drone is assigned to a valid group.
        # Drones already protecting other fields stay in their respective groups.
        # Drones assigned to top field stay in top_group.
        top_assigned = set(currently_protecting_top)

        for d in components:
            if d in top_assigned:
                environment.assign_group(d, top_group)
            else:
                if d.state == "protecting" and d.target_id is not None:
                    other_group = f"protecting {d.target_id}"
                    if other_group in group_ids:
                        environment.assign_group(d, other_group)
                    else:
                        environment.assign_group(d, "idle")
                elif d.state == "moving_to_field" and d.target_id is not None:
                    other_group = f"protecting {d.target_id}"
                    if other_group in group_ids:
                        environment.assign_group(d, other_group)
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")