import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Get fields that are under threat.
        threat_fields = [f for f in environment.fields if f.threat_level > 0]

        # If no field is threatened, set all drones to idle.
        if not threat_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Prepare a set of all drones available for assignment.
        available_drones = set(components)

        # For each threatened field, first gather drones already assigned to it.
        # We'll then process the fields in order of descending threat level.
        field_to_initial = {}
        for field in threat_fields:
            current = [comp for comp in components if comp.target_id == field.id]
            field_to_initial[field.id] = current

        # Process threatened fields, starting with the highest threat.
        sorted_fields = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
        for field in sorted_fields:
            group_name = f"protecting {field.id}"
            required_drones = field.drones_for_full_protection

            # Drones already heading toward or protecting the field.
            current_assigned = field_to_initial[field.id]
            count_assigned = len(current_assigned)

            # If already fully protected, assign these drones and remove from available set.
            if count_assigned >= required_drones:
                for comp in current_assigned:
                    environment.assign_group(comp, group_name)
                    if comp in available_drones:
                        available_drones.remove(comp)
                continue

            # Calculate additional drones needed.
            additional_needed = required_drones - count_assigned

            # Compute the field center.
            center_x = (field.left + field.right) / 2.0
            center_y = (field.top + field.bottom) / 2.0

            # From available drones, choose the ones closest to the field center.
            candidates = list(available_drones)
            candidates.sort(key=lambda comp: ((comp.location.x - center_x) ** 2 +
                                              (comp.location.y - center_y) ** 2))
            selected = candidates[:additional_needed]

            # Combine the drones already assigned with the newly selected ones.
            total_assigned = current_assigned + selected

            # Assign all these drones to protect the field.
            for comp in total_assigned:
                environment.assign_group(comp, group_name)
                if comp in available_drones:
                    available_drones.remove(comp)

        # For any drones that haven't been assigned to any field, assign them as idle.
        for comp in available_drones:
            environment.assign_group(comp, "idle")
