from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Sort fields by threat level in descending order
        threatened_fields = sorted(
            [field for field in environment.fields if field.threat_level > 0],
            key=lambda field: field.threat_level,
            reverse=True
        )

        # Step 2: Collect idle and available drones
        idle_drones = [drone for drone in components if drone.state == "idle"]

        # Step 3: Assign drones to fields
        for field in threatened_fields:
            # Calculate how many more drones are needed for full protection
            needed_drones = max(0, field.necessary_drones_for_full_protection -
                                (field.protecting_drones + field.arriving_drones))

            if needed_drones > 0:
                # Sort idle drones by distance to the field (for efficiency)
                idle_drones.sort(key=lambda drone:
                abs(drone.location.x - (field.left + field.right) / 2) +
                abs(drone.location.y - (field.top + field.bottom) / 2)
                                 )

                # Assign the closest available drones to the field
                assigned_drones = idle_drones[:needed_drones]
                for drone in assigned_drones:
                    environment.assign_group(drone, f"protecting {field.id}")

                # Remove assigned drones from idle list
                idle_drones = idle_drones[needed_drones:]

        # Step 4: Any remaining drones stay idle
        for drone in idle_drones:
            environment.assign_group(drone, "idle")
