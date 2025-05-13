from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmDroneCoordinator(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # Retrieve fields and sort by highest threat level
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Create a mapping for easier assignment
        field_drone_counts = {field.id: field.protecting_drones for field in fields}
        necessary_drones = {field.id: field.drones_for_full_protection for field in fields}

        # Assign drones dynamically
        for drone in components:
            assigned = False
            for field in fields:
                # Assign drone to the field if it needs more drones
                if field_drone_counts[field.id] < necessary_drones[field.id]:
                    environment.assign_group(drone, f"protecting {field.id}")
                    field_drone_counts[field.id] += 1
                    assigned = True
                    break  # Move to the next drone

            # If no field needs extra drones, set drone to idle
            if not assigned:
                environment.assign_group(drone, "idle")
