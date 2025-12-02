from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Divide drones into groups:
        - "idle" for drones not protecting any field.
        - "protecting {field_id}" for drones protecting the field with the highest threat.
        """
        # Collect fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Pick the top-threat field
        top_field = max(fields_with_threat, key=lambda fld: getattr(fld, "threat_level", 0))
        top_field_id = getattr(top_field, "id", None)

        # Determine how many drones are needed for full protection
        needed_for_full = getattr(top_field, "drones_for_full_protection", 1)
        if not isinstance(needed_for_full, int) or needed_for_full < 0:
            needed_for_full = 1

        # Assign drones: first N to protect the top field, rest idle
        assigned_to_top = 0
        top_group = f"protecting {top_field_id}"

        for c in components:
            if assigned_to_top < needed_for_full:
                environment.assign_group(c, top_group)
                assigned_to_top += 1
            else:
                environment.assign_group(c, "idle")