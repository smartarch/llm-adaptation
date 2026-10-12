import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the top-threat field (threat_level > 0)
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_field_id = top_field.id

        # Compute field center
        top_cx = (top_field.left + top_field.right) / 2.0
        top_cy = (top_field.top + top_field.bottom) / 2.0

        def dist_to_top(d):
            dx = getattr(d.location, "x", 0.0) - top_cx
            dy = getattr(d.location, "y", 0.0) - top_cy
            return math.hypot(dx, dy)

        # How many drones are needed for full protection
        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Reserved drones: those already targeting the top field (protecting or moving_to_field)
        reserved = []
        others = []
        for d in components:
            if getattr(d, "target_id", None) == top_field_id:
                reserved.append(d)
            else:
                others.append(d)

        assigned = []

        # If we already have enough reserved drones, keep exactly 'needed' of them
        if len(reserved) >= needed:
            assigned = reserved[:needed]
        else:
            # Use all reserved, then pick closest from the rest
            assigned = list(reserved)
            remaining_needed = needed - len(assigned)
            if remaining_needed > 0:
                others_sorted = sorted(others, key=lambda d: dist_to_top(d))
                assigned.extend(others_sorted[:remaining_needed])

        # Assign the chosen drones to protecting the top field
        for d in assigned:
            environment.assign_group(d, f"protecting {top_field_id}")

        # All other drones idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")