from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Sort fields by descending threat level
        fields_by_threat = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Prepare a dictionary to store drone assignments
        drones_assigned = {field.id: 0 for field in environment.fields}
        idle_group = "idle"

        # Assign drones to fields based on threat priority
        for drone in components:
            if drone.state == "protecting":
                # Already assigned, count towards protection
                if drone.target_id:
                    drones_assigned[drone.target_id] += 1
                continue

            if drone.state == "moving to field":
                # Count drones that are already en route
                if drone.target_id:
                    drones_assigned[drone.target_id] += 1
                continue

        # Now, assign idle drones to fields based on need
        for field in fields_by_threat:
            if field.threat_level == 0:
                continue  # No need to protect this field

            needed_drones = field.necessary_drones_for_full_protection - (
                    field.protecting_drones + field.arriving_drones + drones_assigned[field.id]
            )

            if needed_drones > 0:
                for drone in components:
                    if drone.state == "idle":
                        environment.assign_group(drone, f"protecting {field.id}")
                        drones_assigned[field.id] += 1
                        needed_drones -= 1
                        if needed_drones == 0:
                            break  # Move to next field

        # Assign remaining idle drones to "idle"
        for drone in components:
            if drone.state == "idle":
                environment.assign_group(drone, idle_group)
