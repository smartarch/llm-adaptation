from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Reset all drones to the idle group first
        for component in components:
            environment.assign_group(component, "idle")

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
                    if component.state == "idle"
                ]

                # Start with assigning idle drones if available
                for drone in available_idle_drones[:drones_to_assign]:
                    environment.assign_group(drone, f"protecting {field.id}")

                # If there are not enough idle drones, check for drones moving towards this field
                drones_to_assign_after_idle = drones_to_assign - len(available_idle_drones)
                if drones_to_assign_after_idle > 0:
                    moving_drones = [
                        component for component in components 
                        if component.state == "moving_to_field" and component.target_id == field.id
                    ]

                    for drone in moving_drones[:drones_to_assign_after_idle]:
                        environment.assign_group(drone, f"protecting {field.id}")