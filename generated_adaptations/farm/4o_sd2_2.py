from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Extract fields and sort by highest threat level
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Extract drones
        idle_drones = [drone for drone in components if drone.state == "idle"]
        moving_drones = [drone for drone in components if drone.state == "moving_to_field"]
        protecting_drones = [drone for drone in components if drone.state == "protecting"]

        # Assign drones to fields
        for field in threatened_fields:
            needed_drones = field.necessary_drones_for_full_protection - (field.arriving_drones + field.protecting_drones)
            if needed_drones > 0:
                assigned_drones = min(needed_drones, len(idle_drones))
                for _ in range(assigned_drones):
                    drone = idle_drones.pop()
                    environment.assign_group(drone, f"protecting {field.id}")

        # Any remaining drones stay idle
        for drone in idle_drones:
            environment.assign_group(drone, "idle")
