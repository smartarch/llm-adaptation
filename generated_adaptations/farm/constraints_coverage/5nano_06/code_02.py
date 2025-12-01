from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, set all drones to idle
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        highest_field = max(threat_fields, key=lambda f: f.threat_level)

        # How many drones are required for full protection of this field
        needed = int(getattr(highest_field, "drones_for_full_protection", len(components)))

        # Current drones protecting this field
        current_protect = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == highest_field.id
        ]
        current_count = len(current_protect)

        field_center_x = (highest_field.left + highest_field.right) / 2.0
        field_center_y = (highest_field.top + highest_field.bottom) / 2.0

        def dist2_to_field(d):
            loc = getattr(d, "location", None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, "x", 0) - field_center_x
            dy = getattr(loc, "y", 0) - field_center_y
            return dx * dx + dy * dy

        # If already fully protected, keep existing protecting drones, others idle
        if current_count >= needed:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == highest_field.id:
                    environment.assign_group(d, f"protecting {highest_field.id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Need to assign more drones to protect this field
        # Candidates are drones not currently protecting this field
        candidates = [
            d for d in components
            if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == highest_field.id)
        ]
        # Sort candidates by closeness to the field center
        candidates.sort(key=dist2_to_field)

        to_assign = int(needed) - current_count
        assigned = 0
        for d in candidates:
            if assigned >= to_assign:
                break
            environment.assign_group(d, f"protecting {highest_field.id}")
            assigned += 1

        # Finally, re-assign all drones to explicit groups:
        # - Drones protecting the highest field stay in that group
        # - All others go to idle
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == highest_field.id:
                environment.assign_group(d, f"protecting {highest_field.id}")
            else:
                environment.assign_group(d, "idle")