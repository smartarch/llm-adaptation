from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Extract fields with threats
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]

        # Sort fields by highest threat level first
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Get all available drones
        idle_drones = [drone for drone in components if drone.state == "idle"]
        moving_drones = [drone for drone in components if drone.state == "moving_to_field"]
        protecting_drones = [drone for drone in components if drone.state == "protecting"]

        # Assign drones to protect the highest threat fields first
        for field in threatened_fields:
            field_group_id = f"protecting {field.id}"
            if field_group_id not in group_ids:
                continue  # Skip if the group is not valid

            # Calculate how many more drones are needed
            needed_drones = max(0, field.necessary_drones_for_full_protection -
                                (field.arriving_drones + field.protecting_drones))

            if needed_drones > 0:
                # Sort idle drones by distance to the field
                idle_drones.sort(key=lambda d: self._distance(d.location, field))

                # Assign the closest idle drones
                for _ in range(min(needed_drones, len(idle_drones))):
                    drone = idle_drones.pop(0)
                    environment.assign_group(drone, field_group_id)

        # Assign any remaining idle drones to "idle" group
        for drone in idle_drones:
            environment.assign_group(drone, "idle")

    def _distance(self, location, field):
        """Calculate the Euclidean distance from the drone to the center of the field."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return ((location.x - field_center_x) ** 2 + (location.y - field_center_y) ** 2) ** 0.5
