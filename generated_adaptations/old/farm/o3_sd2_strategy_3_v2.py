import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Create a working copy of available drones.
        available_drones = list(components)

        # Filter out fields that are under threat.
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        if not threatened_fields:
            for drone in available_drones:
                environment.assign_group(drone, "idle")
            return

        # Sort the fields by descending threat level so the highest is processed first.
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Function to compute Euclidean distance from a drone to the center of a field.
        def distance_to_field(drone, field):
            center_x = (field.left + field.right) / 2
            center_y = (field.top + field.bottom) / 2
            return math.hypot(drone.location.x - center_x, drone.location.y - center_y)

        # Process each threatened field in order.
        for field in threatened_fields:
            # Calculate how many drones are already arriving or protecting the field.
            drones_already_assigned = field.arriving_drones + field.protecting_drones

            # Determine how many additional drones are needed for full protection.
            additional_required = field.drones_for_full_protection - drones_already_assigned

            if additional_required <= 0:
                # If the field is already fully protected, skip assignment.
                continue

            # Sort available drones by distance to the field center.
            available_drones.sort(key=lambda drone: distance_to_field(drone, field))

            # Assign the closest drones until the requirement is met.
            assigned = 0
            drones_to_assign = []
            for drone in available_drones:
                if assigned < additional_required:
                    drones_to_assign.append(drone)
                    assigned += 1
                else:
                    break

            # Assign these drones to protect the field.
            group_name = f"protecting {field.id}"
            for drone in drones_to_assign:
                environment.assign_group(drone, group_name)
                available_drones.remove(drone)

        # Any remaining drones are set to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
