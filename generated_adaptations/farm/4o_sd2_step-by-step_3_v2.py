from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Get all fields sorted by threat level (highest first)
        threatened_fields = sorted(
            [field for field in environment.fields if field.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # Dictionary to store drone assignments
        drone_assignments = {drone: "idle" for drone in components}

        # Function to calculate distance between a drone and a field
        def distance(drone, field):
            field_center_x = (field.left + field.right) / 2
            field_center_y = (field.top + field.bottom) / 2
            return ((drone.location.x - field_center_x) ** 2 + (drone.location.y - field_center_y) ** 2) ** 0.5

        # Assign drones to fields based on threat level
        for field in threatened_fields:
            # Determine how many additional drones are needed
            required_drones = field.drones_for_full_protection - field.protecting_drones - field.arriving_drones
            if required_drones <= 0:
                continue  # This field is already fully protected

            # Get drones that are already protecting this field and keep them assigned
            protecting_drones = [drone for drone in components if drone.state == "protecting" and drone.target_id == field.id]
            for drone in protecting_drones:
                drone_assignments[drone] = f"protecting {field.id}"

            # We do NOT subtract protecting drones again from `required_drones` here.

            # Sort remaining available drones by proximity to the field
            available_drones = [drone for drone in components if drone_assignments[drone] == "idle"]
            available_drones.sort(key=lambda d: distance(d, field))

            # Assign the closest available drones up to the required number
            for i in range(min(required_drones, len(available_drones))):
                drone_assignments[available_drones[i]] = f"protecting {field.id}"

        # Assign the drones to their respective groups
        for drone, group_id in drone_assignments.items():
            environment.assign_group(drone, group_id)
