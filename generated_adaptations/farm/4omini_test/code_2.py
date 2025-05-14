from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize a set to keep track of assigned drones
        assigned_drones = set()

        # First, set all drones to be in the idle group by default
        for component in components:
            environment.assign_group(component, "idle")
            assigned_drones.add(component)

        # Evaluate fields and assign necessary drones
        for field in environment.fields:
            if field.threat_level > 0:
                necessary_drones = field.drones_for_full_protection
                protecting_drones = field.protecting_drones
                arriving_drones = field.arriving_drones
                
                # Calculate how many more drones are needed
                drones_needed = necessary_drones - protecting_drones - arriving_drones
                drones_to_assign = max(drones_needed, 0)

                # Filter out drones that are assigned or currently protecting
                available_drones = [
                    component for component in components 
                    if component.state == "idle" and component not in assigned_drones
                ]

                # Assign as many available drones as needed
                for i in range(min(len(available_drones), drones_to_assign)):
                    environment.assign_group(available_drones[i], f"protecting {field.id}")
                    assigned_drones.add(available_drones[i])  # Mark this drone as assigned