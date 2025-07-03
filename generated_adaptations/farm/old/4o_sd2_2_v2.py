from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Extract fields and sort them by threat level (highest first)
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Extract drones
        all_drones = list(components)
        assigned_drones = set()  # Track which drones have been assigned

        # Allocate drones to protect fields
        for field in threatened_fields:
            # Calculate drones needed for full protection
            total_needed = field.drones_for_full_protection
            current = field.protecting_drones + field.arriving_drones

            # Drones needed to reach full protection
            needed_drones = max(0, total_needed - current)

            if needed_drones > 0:
                available_drones = [d for d in all_drones if d not in assigned_drones]
                assigned_count = min(needed_drones, len(available_drones))

                for i in range(assigned_count):
                    drone = available_drones[i]
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_drones.add(drone)

        # Any remaining drones should go to idle
        for drone in all_drones:
            if drone not in assigned_drones:
                environment.assign_group(drone, "idle")
