import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Top-threat field (highest threat level)
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_field_id = top_field.id

        # Field center
        top_center = ((top_field.left + top_field.right) / 2.0,
                      (top_field.top + top_field.bottom) / 2.0)

        # Distance from a drone to the top field center
        def dist_to_top(drone):
            dx = getattr(drone.location, "x", 0.0) - top_center[0]
            dy = getattr(drone.location, "y", 0.0) - top_center[1]
            return math.hypot(dx, dy)

        # Drones needed to fully protect the top field
        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones currently targeting the top field (reserved)
        reserved = []
        for d in components:
            tid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            # Consider drones already headed to or protecting the top field as reserved
            if tid == top_field_id or (st == "moving_to_field" and tid == top_field_id):
                reserved.append(d)

        # Assigned drones to top field
        assigned_to_top = list(reserved)

        # If we don't have enough, bring in closest available drones from the pool
        if len(assigned_to_top) < needed:
            pool = [d for d in components if d not in assigned_to_top]
            pool.sort(key=lambda d: dist_to_top(d))
            needed_more = needed - len(assigned_to_top)
            assigned_to_top.extend(pool[:needed_more])

        # Apply groups: all drones assigned to protect the top field
        for d in assigned_to_top:
            environment.assign_group(d, f"protecting {top_field_id}")

        # All other drones idle
        for d in components:
            if d not in assigned_to_top:
                environment.assign_group(d, "idle")