from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Extract relevant information
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)  # Sort fields by threat level
        drones = list(components)  # List of drones

        # Grouping available drones
        protecting_drones = {field.id: field.protecting_drones for field in fields}
        arriving_drones = {field.id: field.arriving_drones for field in fields}
        necessary_drones = {field.id: field.necessary_drones_for_full_protection for field in fields}

        # Track assignments
        assignments = {drone: "idle" for drone in drones}

        # Identify currently protecting drones
        protecting_now = {field.id: [] for field in fields}
        for drone in drones:
            if drone.state == "protecting" and drone.target_id in protecting_now:
                protecting_now[drone.target_id].append(drone)

        # Assign drones to protect fields
        unassigned_drones = [d for d in drones if assignments[d] == "idle"]

        for field in fields:
            if field.threat_level > 0:
                field_id = field.id
                required = necessary_drones[field_id] - (protecting_drones[field_id] + arriving_drones[field_id])

                # Keep existing protecting drones
                for drone in protecting_now[field_id]:
                    assignments[drone] = f"protecting {field_id}"
                    required -= 1

                # Assign nearest available drones
                if required > 0:
                    unassigned_drones.sort(key=lambda d: ((d.location.x - (field.left + field.right) / 2) ** 2 +
                                                          (d.location.y - (field.top + field.bottom) / 2) ** 2) ** 0.5)
                    for _ in range(required):
                        if unassigned_drones:
                            drone = unassigned_drones.pop(0)
                            assignments[drone] = f"protecting {field_id}"

        # Perform assignments
        for drone, group in assignments.items():
            environment.assign_group(drone, group)
