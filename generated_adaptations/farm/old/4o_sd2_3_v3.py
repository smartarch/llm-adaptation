from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Sort fields by descending threat level
        fields_by_threat = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # Calculate how many more drones each field needs
        needed_drones = {}
        for field in fields_by_threat:
            current = field.protecting_drones + field.arriving_drones
            needed = max(0, field.drones_for_full_protection - current)
            needed_drones[field.id] = needed

        # Assign drones to fields based on threat level and remaining need
        unassigned_drones = list(components)  # all drones need to be reassigned

        for field in fields_by_threat:
            count = 0
            for drone in unassigned_drones[:]:  # iterate over a copy
                if count >= needed_drones[field.id]:
                    break
                environment.assign_group(drone, f"protecting {field.id}")
                unassigned_drones.remove(drone)
                count += 1

        # Assign any remaining drones to "idle"
        for drone in unassigned_drones:
            environment.assign_group(drone, "idle")
