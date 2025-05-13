from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmDroneAssignment(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # Sort fields by highest threat level
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Categorize drones
        idle_drones = [d for d in components if d.target is None]
        protecting_drones = {f.id: [] for f in fields}

        for d in components:
            if d.target:
                protecting_drones[d.target].append(d)

        # Assign drones based on threat level and need for full protection
        for field in fields:
            needed_drones = field.drones_for_full_protection - len(protecting_drones[field.id])
            if needed_drones > 0:
                assigned_drones = min(len(idle_drones), needed_drones)
                for _ in range(assigned_drones):
                    drone = idle_drones.pop()
                    environment.assign_group(drone, f"protecting {field.id}")

        # If drones are left, assign to the most threatened field
        while idle_drones:
            field = max(fields, key=lambda f: f.threat_level)
            drone = idle_drones.pop()
            environment.assign_group(drone, f"protecting {field.id}")
