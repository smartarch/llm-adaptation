from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Get a list of active fields that require protection
        threatened_fields = [
            field for field in environment.fields if field.threat_level > 0
        ]

        # Sort fields by highest threat level (descending)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Available drones
        idle_drones = [drone for drone in components if drone.state == "idle"]

        # Assign drones based on need
        for field in threatened_fields:
            # Calculate how many drones are still needed for full protection
            needed_drones = (
                    field.drones_for_full_protection
                    - field.protecting_drones
                    - field.arriving_drones
            )

            if needed_drones > 0:
                assigned_drones = idle_drones[:needed_drones]
                for drone in assigned_drones:
                    environment.assign_group(drone, f"protecting {field.id}")

                # Remove assigned drones from the idle pool
                idle_drones = idle_drones[needed_drones:]

            # If no more idle drones are available, stop assignment
            if not idle_drones:
                break

        # Any remaining drones stay idle
        for drone in idle_drones:
            environment.assign_group(drone, "idle")
