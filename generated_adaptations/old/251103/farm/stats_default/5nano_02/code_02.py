import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat > 0
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            # No threat fields: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat level
        best_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        field_id = best_field.id

        # Field center for distance calculations
        cx = (best_field.left + best_field.right) / 2.0
        cy = (best_field.top + best_field.bottom) / 2.0

        # Drones already targeting the best field (committed)
        committed = [c for c in components if c.target_id == field_id]
        committed_count = len(committed)

        # Required drones for full protection
        required = int(getattr(best_field, "drones_for_full_protection", 0))

        # If there is nothing to protect or there are enough drones already committed
        if required <= 0 or committed_count >= required:
            # Ensure all drones targeting this field are in its protecting group
            committed_ids = {id(c) for c in committed}
            for c in components:
                if id(c) in committed_ids:
                    environment.assign_group(c, f"protecting {field_id}")
                else:
                    environment.assign_group(c, "idle")
            return

        # Otherwise, we need to allocate additional drones: pick the closest available ones
        # Drones not currently targeting the field
        candidates = [c for c in components if c.target_id != field_id]

        def dist2_to_field(d):
            dx = getattr(d.location, "x", 0.0) - cx
            dy = getattr(d.location, "y", 0.0) - cy
            return dx * dx + dy * dy

        candidates.sort(key=dist2_to_field)

        need = min(required - committed_count, len(candidates))
        to_assign = candidates[:need]

        # Assign groups: those committed or newly assigned go to protecting {field_id}
        target_ids = {id(c) for c in committed}  # already committed to field
        target_ids.update({id(c) for c in to_assign})

        for c in components:
            if id(c) in target_ids:
                environment.assign_group(c, f"protecting {field_id}")
            else:
                environment.assign_group(c, "idle")