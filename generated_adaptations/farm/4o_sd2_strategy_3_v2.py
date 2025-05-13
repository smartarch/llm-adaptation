from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Sort fields by threat level in descending order
        threatened_fields = sorted(
            [field for field in environment.fields if field.threat_level > 0],
            key=lambda field: field.threat_level,
            reverse=True
        )

        # Step 2: Collect all drones (idle, moving, protecting)
        all_drones = list(components)  # All drones are considered for reassignment

        # Step 3: Assign drones to fields
        assigned_drones = set()
        for field in threatened_fields:
            # Calculate how many more drones are needed for full protection
            needed_drones = max(0, field.drones_for_full_protection -
                                (field.protecting_drones + field.arriving_drones))

            if needed_drones > 0:
                # Sort drones by distance to the field (to minimize travel time)
                all_drones.sort(key=lambda drone:
                abs(drone.location.x - (field.left + field.right) / 2) +
                abs(drone.location.y - (field.top + field.bottom) / 2)
                                )

                # Assign the closest available drones to the field
                selected_drones = [drone for drone in all_drones if drone not in assigned_drones][:needed_drones]
                for drone in selected_drones:
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_drones.add(drone)

        # Step 4: Any remaining drones stay idle
        for drone in all_drones:
            if drone not in assigned_drones:
                environment.assign_group(drone, "idle")
