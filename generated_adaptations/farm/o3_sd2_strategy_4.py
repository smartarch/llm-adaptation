import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with a threat level > 0.
        threat_fields = [f for f in environment.fields if f.threat_level > 0]

        # If no fields are under threat, set all drones as idle.
        if not threat_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Select the field with the highest threat level.
        primary_field = max(threat_fields, key=lambda f: f.threat_level)
        protecting_group = f"protecting {primary_field.id}"

        # Determine how many drones are required for full protection.
        # The field provides the number needed for full protection.
        required_drones = primary_field.necessary_drones_for_full_protection

        # Count drones already heading to or protecting the primary field.
        current_assigned = [comp for comp in components if comp.target_id == primary_field.id]
        current_count = len(current_assigned)

        # Calculate how many additional drones are needed.
        additional_needed = max(0, required_drones - current_count)

        # Compute the center of the primary field.
        center_x = (primary_field.left + primary_field.right) / 2.0
        center_y = (primary_field.top + primary_field.bottom) / 2.0

        # Sort drones not already assigned to the primary field by distance to the field's center.
        available_drones = [comp for comp in components if comp.target_id != primary_field.id]
        available_drones.sort(key=lambda comp: ((comp.location.x - center_x) ** 2 + (comp.location.y - center_y) ** 2))

        # Choose the closest additional drones required to achieve full protection.
        selected_drones = available_drones[:additional_needed]

        # Assign drones to protect the primary field.
        for comp in selected_drones:
            environment.assign_group(comp, protecting_group)
        for comp in current_assigned:
            environment.assign_group(comp, protecting_group)

        # All remaining drones are set as idle.
        assigned_drones = set(selected_drones + current_assigned)
        for comp in components:
            if comp not in assigned_drones:
                environment.assign_group(comp, "idle")
