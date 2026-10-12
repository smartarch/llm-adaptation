from typing import List

# Assuming the base class is importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Find the field with the highest threat level (> 0)
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            # Only consider fields with positive threat
            if getattr(f, "threat_level", 0) > 0 and getattr(f, "threat_level") > max_threat:
                max_threat = f.threat_level
                top_field = f

        # If no field needs protection, idle all drones
        if top_field is None:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Count drones currently protecting the top field
        current_protecting = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                current_protecting += 1

        # If already fully protected, keep exactly drones_for_full_protection drones on that field
        if current_protecting >= top_field.drones_for_full_protection:
            kept = 0
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                    if kept < top_field.drones_for_full_protection:
                        environment.assign_group(c, f"protecting {top_field.id}")
                        kept += 1
                    else:
                        environment.assign_group(c, "idle")
                else:
                    environment.assign_group(c, "idle")
            return

        # Need more drones to fully protect the top field
        needed = int(top_field.drones_for_full_protection - current_protecting)

        # Compute field center
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        # Compute distances (squared) from each drone to the field center
        drones_with_dist = []
        for c in components:
            loc = getattr(c, "location", None)
            if loc is None:
                # If no location info, treat as far away
                dist2 = float('inf')
            else:
                dx = loc.x - center_x
                dy = loc.y - center_y
                dist2 = dx*dx + dy*dy
            drones_with_dist.append((dist2, c))

        # Sort by distance (closest first)
        drones_with_dist.sort(key=lambda t: t[0])

        # Pick the closest 'needed' drones
        chosen_drones = [d for _, d in drones_with_dist[:needed]]

        # Assign chosen drones to protect the top field, others idle
        for c in components:
            if c in chosen_drones:
                environment.assign_group(c, f"protecting {top_field.id}")
            else:
                environment.assign_group(c, "idle")