from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Prioritize drones that are idle
        available_drones = sorted(components, key=lambda d: 0 if d.state == "idle" else 1)

        # Iterate over each field with threat level > 0 and assign drones
        for field in environment.fields:
            if field.threat_level > 0:
                # Determine how many drones are still needed for full protection
                already_assigned = field.arriving_drones + field.protecting_drones
                drones_needed = max(0, field.drones_for_full_protection - already_assigned)

                # Create the group id for protecting this field
                group_name = f"protecting {field.id}"

                # Only assign as many drones as required from our available pool
                for _ in range(drones_needed):
                    if available_drones:
                        drone = available_drones.pop(0)
                        environment.assign_group(drone, group_name)

        # Any drones that remain unassigned are set to idle
        for drone in available_drones:
            environment.assign_group(drone, "idle")
