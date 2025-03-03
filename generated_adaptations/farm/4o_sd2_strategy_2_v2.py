from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Extract threatened fields sorted by highest threat first
        threatened_fields = sorted(
            [field for field in environment.fields if field.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # Categorize drones
        idle_drones = [drone for drone in components if drone.state == "idle"]
        moving_drones = [drone for drone in components if drone.state == "moving to field"]
        protecting_drones = [drone for drone in components if drone.state == "protecting"]

        # Dictionary to track drones already assigned to fields
        field_drones = {field.id: [] for field in environment.fields}

        # Collect all drones currently moving or protecting
        for drone in moving_drones + protecting_drones:
            if drone.target_id:
                field_drones[drone.target_id].append(drone)

        # Assign drones to high-threat fields first
        for field in threatened_fields:
            field_group_id = f"protecting {field.id}"
            if field_group_id not in group_ids:
                continue  # Skip if group is not valid

            # Compute total drones already assigned to this field
            total_assigned = len(field_drones[field.id]) + field.arriving_drones + field.protecting_drones
            needed_drones = max(0, field.necessary_drones_for_full_protection - total_assigned)

            # Get closest idle/moving drones
            available_drones = sorted(
                idle_drones + moving_drones, key=lambda d: self._distance(d.location, field)
            )

            # Assign the closest available drones
            for _ in range(min(needed_drones, len(available_drones))):
                drone = available_drones.pop(0)
                environment.assign_group(drone, field_group_id)
                field_drones[field.id].append(drone)

        # If any field has **too many** drones, move some to other fields
        for field in threatened_fields:
            field_group_id = f"protecting {field.id}"
            if field_group_id not in group_ids:
                continue

            # Compute excess drones
            total_assigned = len(field_drones[field.id]) + field.arriving_drones + field.protecting_drones
            excess_drones = max(0, total_assigned - field.necessary_drones_for_full_protection)

            if excess_drones > 0:
                excess_list = sorted(
                    field_drones[field.id], key=lambda d: self._distance(d.location, field), reverse=True
                )
                for _ in range(excess_drones):
                    if excess_list:
                        drone = excess_list.pop(0)
                        environment.assign_group(drone, "idle")

        # Assign any remaining idle drones to "idle"
        for drone in idle_drones:
            environment.assign_group(drone, "idle")

    def _distance(self, location, field):
        """Calculate Euclidean distance from drone to the center of the field."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return ((location.x - field_center_x) ** 2 + (location.y - field_center_y) ** 2) ** 0.5
