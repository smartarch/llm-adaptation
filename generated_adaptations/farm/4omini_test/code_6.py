from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize the assignment tracking
        assigned_drones = set()

        # Filter fields based on their threat levels for priority assignment
        threat_fields = [
            field for field in environment.fields if field.threat_level > 0
        ]
        # Sort the fields by threat level in descending order (highest first)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Get available drones
        available_drones = [component for component in components if component.state == "idle"]
        moving_drones = [component for component in components if component.state == "moving_to_field"]

        # Assign drones to fields based on priority
        for field in threat_fields:
            necessary_drones = field.drones_for_full_protection
            protecting_drones = field.protecting_drones
            arriving_drones = field.arriving_drones
            
            # Calculate how many more drones are needed
            drones_needed = necessary_drones - protecting_drones - arriving_drones
            if drones_needed <= 0:
                continue  # Field is already adequately protected

            # First assign idle drones to the field
            idle_to_assign = min(len(available_drones), max(drones_needed, 0))
            for drone in available_drones[:idle_to_assign]:
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_drones.add(drone)

            # Update the list of available drones after assignments
            available_drones = available_drones[idle_to_assign:]

            # If more drones are needed, assign moving drones
            drones_needed_after_idle = drones_needed - idle_to_assign
            if drones_needed_after_idle > 0:
                moving_to_assign = min(len(moving_drones), drones_needed_after_idle)
                for drone in moving_drones[:moving_to_assign]:
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_drones.add(drone)

        # Finally, ensure any drones that were not assigned are set to idle
        for component in components:
            if component not in assigned_drones:
                environment.assign_group(component, "idle")