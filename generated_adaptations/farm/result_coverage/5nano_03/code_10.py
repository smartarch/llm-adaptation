import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Pick the top-threat field (highest threat_level)
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_field_id = top_field.id

        # Field center
        top_center = ((top_field.left + top_field.right) / 2.0,
                      (top_field.top + top_field.bottom) / 2.0)

        # Helper: distance from a drone to the top field center
        def dist_to_top(drone):
            dx = getattr(drone.location, "x", 0.0) - top_center[0]
            dy = getattr(drone.location, "y", 0.0) - top_center[1]
            return math.hypot(dx, dy)

        # How many drones are needed to fully protect the top field
        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones currently targeting the top field (reservations)
        currently_protecting = []
        other_drones = []
        for d in components:
            if getattr(d, "target_id", None) == top_field_id:
                currently_protecting.append(d)
            else:
                other_drones.append(d)

        # Decide which drones will protect the top field
        assigned_to_top = []

        # If we already have enough drones targeting top_field, keep exactly 'needed'
        if len(currently_protecting) >= needed:
            assigned_to_top = currently_protecting[:needed]
        else:
            # Keep all currently protecting, then bring in nearest drones from the pool
            assigned_to_top = list(currently_protecting)
            remaining_needed = needed - len(assigned_to_top)

            if remaining_needed > 0:
                # Pool = drones not currently protecting top_field
                pool = [d for d in components if d not in assigned_to_top]
                pool.sort(key=lambda d: dist_to_top(d))
                assigned_to_top.extend(pool[:remaining_needed])

        # Apply groups: assign the chosen drones to the top_field protection
        for d in assigned_to_top:
            environment.assign_group(d, f"protecting {top_field_id}")

        # All other drones idle
        for d in components:
            if d not in assigned_to_top:
                environment.assign_group(d, "idle")