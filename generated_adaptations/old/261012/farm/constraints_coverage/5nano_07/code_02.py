from typing import List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into groups:
        - "idle": drones not protecting any field
        - "protecting {field_id}": drones protecting a specific field (only for fields with threat > 0)

        Strategy:
        - Find the field with the highest threat_level > 0. If none, idle all drones.
        - Compute how many drones are already protecting that field.
        - Needed = max(0, field.drones_for_full_protection - current_protecting)
        - Reassign the closest available drones (not already protecting this field) to the "protecting {field_id}" group
          until we reach the needed number. Keep currently protecting drones assigned to this field.
        - All other drones go to "idle".
        """
        # 1. Identify the most threatened field
        fields_with_threat = [f for f in getattr(environment, 'fields', []) if getattr(f, 'threat_level', 0) > 0]
        if not fields_with_threat:
            # No field under threat; idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Select the field with the highest threat level
        top_field = max(fields_with_threat, key=lambda f: float(getattr(f, 'threat_level', 0)))

        # Field center coordinates
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        def dist_to_field(drone) -> float:
            loc = getattr(drone, 'location', None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, 'x', 0.0) - center_x
            dy = getattr(loc, 'y', 0.0) - center_y
            return math.hypot(dx, dy)

        # 2. Current protectors for the top field
        current_protectors = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field.id]
        current_count = len(current_protectors)

        # 3. How many drones are needed for full protection
        drones_for_full = getattr(top_field, 'drones_for_full_protection', 1)
        try:
            drones_for_full = int(drones_for_full)
        except (TypeError, ValueError):
            drones_for_full = 1

        needed = max(0, drones_for_full - current_count)

        target_group = f"protecting {top_field.id}"

        # 4. Assign the currently protecting drones to the target group (ensure they stay protecting this field)
        for d in current_protectors:
            environment.assign_group(d, target_group)

        # 5. Pick the closest drones not already protecting this field to fill the gap
        not_current_protecting = [d for d in components if d not in current_protectors]

        not_current_protecting.sort(key=lambda d: dist_to_field(d))

        assigned_set = set(current_protectors)

        for i in range(min(needed, len(not_current_protecting))):
            drone = not_current_protecting[i]
            environment.assign_group(drone, target_group)
            assigned_set.add(drone)

        # 6. Assign all remaining drones to idle (to satisfy the "exactly one group" requirement)
        for d in components:
            if d in assigned_set:
                continue
            environment.assign_group(d, "idle")