from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # First, reassign drones that are already protecting a field.
        free_drones = []
        for drone in components:
            # If drone is already protecting and its target is valid and still under threat, keep it in that group.
            if (drone.state == "protecting" and drone.target_id is not None
                    and f"protecting {drone.target_id}" in group_ids):
                # Check if the field still has a threat. If not, later we will assign idle.
                field = next((f for f in environment.fields if f.id == drone.target_id), None)
                if field and field.threat_level > 0:
                    environment.assign_group(drone, f"protecting {field.id}")
                    continue  # Drone is locked-in.
            # Otherwise, this drone is free to be re-assigned.
            free_drones.append(drone)

        # Compute additional protection needed per field.
        additional_needed = {}
        # For each field with a threat, compute how many more drones are needed
        for field in environment.fields:
            group_name = f"protecting {field.id}"
            if field.threat_level > 0 and group_name in group_ids:
                # Count how many drones are already protecting this field (from current components).
                already_protecting = sum(
                    1 for drone in components
                    if drone.state == "protecting" and drone.target_id == field.id
                )
                # Additional drones needed: required minus those already protecting and drones arriving.
                needed = field.drones_for_full_protection - already_protecting - field.arriving_drones
                additional_needed[field.id] = max(0, needed)

        # Sort the fields by descending threat level (fields with higher threat get priority).
        fields_sorted = sorted(
            [field for field in environment.fields if field.threat_level > 0 and f"protecting {field.id}" in group_ids],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # Assign free drones to fields that need additional protection.
        for drone in free_drones:
            assigned = False
            for field in fields_sorted:
                if additional_needed.get(field.id, 0) > 0:
                    environment.assign_group(drone, f"protecting {field.id}")
                    additional_needed[field.id] -= 1
                    assigned = True
                    break
            # If no field needs more drones, mark the drone as idle.
            if not assigned:
                environment.assign_group(drone, "idle")
