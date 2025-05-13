import abc
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Identify all fields that need protection (sorted by threat level)
        threat_fields = [field for field in environment.fields if field.threat_level > 0]
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Step 2: Collect all drones (idle, moving, protecting)
        all_drones = list(components)  # Make a copy to modify
        idle_drones = [drone for drone in all_drones if drone.state == "idle"]
        moving_drones = [drone for drone in all_drones if drone.state == "moving to field"]
        protecting_drones = {drone.target_id: [] for drone in all_drones if drone.state == "protecting"}

        for drone in all_drones:
            if drone.state == "protecting":
                protecting_drones[drone.target_id].append(drone)

        # Step 3: Assign drones based on highest-threat fields
        assigned_drones = set()
        for field in threat_fields:
            # Calculate how many more drones are needed
            needed_drones = (
                    field.drones_for_full_protection - field.protecting_drones - field.arriving_drones
            )

            # If the field is fully protected, continue
            if needed_drones <= 0:
                continue

            # Step 3.1: Find the closest drones (idle or moving)
            available_drones = sorted(
                (idle_drones + moving_drones), key=lambda d: self.distance(d, field)
            )

            for _ in range(min(needed_drones, len(available_drones))):
                drone = available_drones.pop(0)
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_drones.add(drone)

        # Step 4: Reassign excess drones from overprotected fields
        for field in protecting_drones:
            if field not in [f.id for f in threat_fields]:
                continue  # Skip fields that are no longer under threat

            excess_drones = max(0, len(protecting_drones[field]) - field.drones_for_full_protection)
            if excess_drones > 0:
                for _ in range(excess_drones):
                    drone = protecting_drones[field].pop()
                    environment.assign_group(drone, "idle")  # Move excess drones to idle

        # Step 5: Unassigned drones remain idle
        for drone in all_drones:
            if drone not in assigned_drones:
                environment.assign_group(drone, "idle")

    def distance(self, drone, field):
        """ Compute Euclidean distance between a drone and the center of a field. """
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return math.sqrt((drone.location.x - field_center_x) ** 2 + (drone.location.y - field_center_y) ** 2)
