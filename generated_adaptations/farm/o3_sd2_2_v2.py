from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Build a lookup for fields by id
        field_map = {field.id: field for field in environment.fields}

        # Preserve drones already protecting a threatened field:
        preserved_drones = set()
        for drone in components:
            if drone.state == "protecting" and drone.target_id is not None:
                # Only preserve if the field still has a threat
                if drone.target_id in field_map and field_map[drone.target_id].threat_level > 0:
                    environment.assign_group(drone, f"protecting {drone.target_id}")
                    preserved_drones.add(drone)

        # List drones available for new assignments (i.e. not already preserving a threatened field)
        available_drones = [d for d in components if d not in preserved_drones]

        # For each field with a threat, assign additional drones if necessary.
        for field in environment.fields:
            if field.threat_level > 0:
                # Determine the additional drones needed using sensor data.
                additional_needed = max(0, field.necessary_drones_for_full_protection - (field.arriving_drones + field.protecting_drones))

                # Assign additional drones from our available pool.
                for _ in range(additional_needed):
                    if available_drones:
                        drone = available_drones.pop(0)
                        environment.assign_group(drone, f"protecting {field.id}")

        # Finally, assign any remaining drones to the idle group.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
