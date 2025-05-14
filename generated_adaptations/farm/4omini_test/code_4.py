from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize a set to keep track of assigned drones
        assigned_drones = set()

        # Evaluate fields and assign necessary drones
        for field in environment.fields:
            if field.threat_level > 0:
                necessary_drones = field.drones_for_full_protection
                protecting_drones = field.protecting_drones
                arriving_drones = field.arriving_drones
                
                # Calculate how many more drones are needed
                drones_needed = necessary_drones - protecting_drones - arriving_drones
                drones_to_assign = max(drones_needed, 0)

                # Get idle drones
                available_idle_drones = [
                    component for component in components 
                    if component.state == "idle" and component not in assigned_drones
                ]

                # Assign idle drones first
                for drone in available_idle_drones[:drones_to_assign]:
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_drones.add(drone)

                # If there are still druons to assign, check for drones moving towards this field
                remaining_drones_to_assign = drones_to_assign - len(available_idle_drones)
                if remaining_drones_to_assign > 0:
                    moving_drones = [
                        component for component in components 
                        if component.state == "moving_to_field" and component.target_id == field.id and component not in assigned_drones
                    ]

                    for drone in moving_drones[:remaining_drones_to_assign]:
                        environment.assign_group(drone, f"protecting {field.id}")
                        assigned_drones.add(drone)

        # Finally, ensure any drones not assigned remain idle
        for component in components:
            if component not in assigned_drones:
                environment.assign_group(component, "idle")