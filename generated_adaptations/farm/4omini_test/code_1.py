from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # First, set all drones to be in the idle group by default
        for component in components:
            environment.assign_group(component, "idle")

        # Evaluate fields and assign necessary drones
        for field in environment.fields:
            if field.threat_level > 0:
                necessary_drones = field.drones_for_full_protection
                protecting_drones = field.protecting_drones
                arriving_drones = field.arriving_drones
                    
                # Calculate available drones
                available_drones = [component for component in components if component.state == "idle"]

                # Determine how many drones to assign to protect the field
                drones_needed = necessary_drones - protecting_drones - arriving_drones
                drones_to_assign = min(len(available_drones), max(drones_needed, 0))

                # Assign the available drones to the field's protection group if needed
                for i in range(drones_to_assign):
                    environment.assign_group(available_drones[i], f"protecting {field.id}")