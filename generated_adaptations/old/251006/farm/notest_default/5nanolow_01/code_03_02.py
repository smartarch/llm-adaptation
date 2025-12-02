from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Simple, constraint-compliant assignment:
        - If there is at least one field with threat_level > 0, assign all drones to
          the group protecting the top-threat field: "protecting {field_id}".
        - Otherwise, assign all drones to "idle".
        """
        # Find fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Identify the top-threat field
        top_field = max(fields_with_threat, key=lambda fld: getattr(fld, "threat_level", 0))
        top_field_id = getattr(top_field, "id", None)
        if top_field_id is None:
            # Fallback: idle if no valid id
            for c in components:
                environment.assign_group(c, "idle")
            return

        top_group = f"protecting {top_field_id}"
        # Ensure the top group is valid; if not, fall back to idle
        if top_group not in group_ids:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Assign all drones to the top protection group
        for c in components:
            environment.assign_group(c, top_group)