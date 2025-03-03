from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Sort fields by threat level (highest first)
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Step 2: Identify drones already assigned to fields
        protecting_drones = {field.id: [] for field in fields}
        idle_drones = []

        for drone in components:
            if drone.target_id and drone.target_id in protecting_drones:
                protecting_drones[drone.target_id].append(drone)
            else:
                idle_drones.append(drone)

        # Step 3: Assign drones to the most threatened fields
        for field in fields:
            required_drones = max(0, field.necessary_drones_for_full_protection - len(protecting_drones[field.id]))

            if required_drones > 0:
                # Sort idle drones by distance to the field
                idle_drones.sort(key=lambda d: self._distance(d.location, field))

                # Assign necessary drones
                assigned_drones = idle_drones[:required_drones]
                protecting_drones[field.id].extend(assigned_drones)
                idle_drones = idle_drones[required_drones:]

            # Assign all protecting drones to the field
            for drone in protecting_drones[field.id]:
                environment.assign_group(drone, f"protecting {field.id}")

        # Step 4: Assign remaining drones to idle
        for drone in idle_drones:
            environment.assign_group(drone, "idle")

    def _distance(self, loc, field):
        """Calculate the Manhattan distance between a drone and a field center."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return abs(loc.x - field_center_x) + abs(loc.y - field_center_y)
