from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Sort fields by descending threat level to prioritize high-threat fields
        fields_by_threat = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Track required drones per field
        drones_needed = {field.id: max(0, field.necessary_drones_for_full_protection - (field.protecting_drones + field.arriving_drones)) for field in environment.fields}

        # Create lists of drones by state
        idle_drones = []
        assigned_drones = {field.id: [] for field in environment.fields}

        for drone in components:
            if drone.state == "idle":
                idle_drones.append(drone)
            elif drone.target_id:
                assigned_drones[drone.target_id].append(drone)

        # Reassign drones from overprotected fields
        for field in fields_by_threat:
            excess_drones = max(0, len(assigned_drones[field.id]) - field.necessary_drones_for_full_protection)
            if excess_drones > 0:
                for _ in range(excess_drones):
                    drone = assigned_drones[field.id].pop()
                    idle_drones.append(drone)

        # Assign drones to fields based on the new priority order
        for field in fields_by_threat:
            needed = drones_needed[field.id]

            while needed > 0 and idle_drones:
                drone = idle_drones.pop()
                environment.assign_group(drone, f"protecting {field.id}")
                needed -= 1

        # Any remaining drones go to "idle"
        for drone in idle_drones:
            environment.assign_group(drone, "idle")
