from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Identify fields that require protection
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)  # Sort by highest threat level

        # Step 2: Collect all drones (idle, moving, and protecting)
        all_drones = list(components)

        # Step 3: Reset drone assignments (reassign all drones dynamically)
        for drone in all_drones:
            environment.assign_group(drone, "idle")  # Reset all drones to idle first

        # Step 4: Assign drones to fields based on their needs
        for field in threatened_fields:
            # Compute number of drones still needed for full protection
            needed_drones = (
                    field.drones_for_full_protection
                    - field.protecting_drones
                    - field.arriving_drones
            )

            if needed_drones > 0:
                # Assign drones up to the needed amount
                assigned_drones = all_drones[:needed_drones]
                for drone in assigned_drones:
                    environment.assign_group(drone, f"protecting {field.id}")

                # Remove assigned drones from the list
                all_drones = all_drones[needed_drones:]

            # Stop assigning if no drones are left
            if not all_drones:
                break

        # Step 5: Any remaining drones stay idle
        for drone in all_drones:
            environment.assign_group(drone, "idle")
