from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Sort fields by threat level (highest first)
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Step 2: Treat all drones as idle initially
        all_drones = list(components)  # Copy the list of drones
        drone_assignments = {drone: "idle" for drone in all_drones}

        # Step 3: Allocate drones to each field based on threat level
        for field in fields:
            required_drones = field.necessary_drones_for_full_protection
            assigned_drones = []

            # Sort drones by proximity to the field
            all_drones.sort(key=lambda d: self._distance(d.location, field))

            # Assign as many drones as necessary
            for drone in all_drones:
                if len(assigned_drones) < required_drones:
                    drone_assignments[drone] = f"protecting {field.id}"
                    assigned_drones.append(drone)

            # Remove assigned drones from available list
            all_drones = [d for d in all_drones if d not in assigned_drones]

        # Step 4: Apply assignments to the environment
        for drone, group in drone_assignments.items():
            environment.assign_group(drone, group)

    def _distance(self, loc, field):
        """Calculate the Manhattan distance between a drone and a field center."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return abs(loc.x - field_center_x) + abs(loc.y - field_center_y)
