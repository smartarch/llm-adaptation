import abc
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Identify all fields that need protection
        threat_fields = [field for field in environment.fields if field.threat_level > 0]
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)  # Sort by threat level (high to low)

        # Step 2: Collect drones by state
        idle_drones = [drone for drone in components if drone.state == "idle"]
        moving_drones = [drone for drone in components if drone.state == "moving_to_field"]
        protecting_drones = {drone.target_id: [] for drone in components if drone.state == "protecting"}

        for drone in components:
            if drone.state == "protecting":
                protecting_drones[drone.target_id].append(drone)

        # Step 3: Assign drones to fields based on highest threat
        assigned_drones = set()
        for field in threat_fields:
            needed_drones = (
                    field.necessary_drones_for_full_protection - field.protecting_drones - field.arriving_drones
            )
            if needed_drones <= 0:
                continue  # Field is already fully protected

            # Step 3.1: Find the closest idle drones
            idle_drones.sort(key=lambda d: self.distance(d, field))
            for _ in range(min(needed_drones, len(idle_drones))):
                drone = idle_drones.pop(0)
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_drones.add(drone)

        # Step 4: Any remaining drones stay idle
        for drone in idle_drones:
            environment.assign_group(drone, "idle")

    def distance(self, drone, field):
        """ Compute Euclidean distance between a drone and the center of a field. """
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return math.sqrt((drone.location.x - field_center_x) ** 2 + (drone.location.y - field_center_y) ** 2)
