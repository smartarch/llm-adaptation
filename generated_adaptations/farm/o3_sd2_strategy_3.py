import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Filter out fields with a threat (threat_level > 0)
        fields_under_threat = [field for field in environment.fields if field.threat_level > 0]

        # If there are no threatened fields, assign all drones to "idle"
        if not fields_under_threat:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Identify the field with the highest threat level
        highest_field = max(fields_under_threat, key=lambda field: field.threat_level)
        target_group = f"protecting {highest_field.id}"

        # Compute the additional drones needed to fully protect the field.
        # Note: highest_field.arriving_drones and highest_field.protecting_drones represent drones already heading for or protecting the field.
        drones_already_assigned = highest_field.arriving_drones + highest_field.protecting_drones
        additional_required = highest_field.necessary_drones_for_full_protection - drones_already_assigned

        # If the field is already fully protected (or over-protected),
        # keep the drones protecting it and assign the rest as "idle".
        if additional_required <= 0:
            for drone in components:
                if drone.target_id == highest_field.id and drone.state in ["moving_to_field", "protecting"]:
                    environment.assign_group(drone, target_group)
                else:
                    environment.assign_group(drone, "idle")
            return

        # Calculate the center of the field
        center_x = (highest_field.left + highest_field.right) / 2
        center_y = (highest_field.top + highest_field.bottom) / 2

        def drone_distance(drone):
            dx = drone.location.x - center_x
            dy = drone.location.y - center_y
            return math.hypot(dx, dy)

        # Sort available drones by their distance to the field center
        sorted_drones = sorted(components, key=drone_distance)

        # Assign the closest drones to the protection group until full protection is achieved.
        drones_assigned = 0
        for drone in sorted_drones:
            if drones_assigned < additional_required:
                environment.assign_group(drone, target_group)
                drones_assigned += 1
            else:
                environment.assign_group(drone, "idle")
