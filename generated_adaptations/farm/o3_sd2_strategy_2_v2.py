import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Create a set of threatened field IDs (fields with a positive threat level).
        threatened_field_ids = {field.id for field in environment.fields if field.threat_level > 0}

        # Build a list of drones that are not already protecting a threatened field.
        available_drones = []
        for drone in components:
            # If drone is protecting a field and that field is still threatened, leave it in its group.
            if drone.state == "protecting" and drone.target_id in threatened_field_ids:
                continue
            # Otherwise, the drone is available for reassignment.
            available_drones.append(drone)

        # For fields with threat level > 0, sort them by descending threat level.
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        threatened_fields.sort(key=lambda field: field.threat_level, reverse=True)

        for field in threatened_fields:
            # Calculate additional drones required for full protection.
            current_assigned = field.arriving_drones + field.protecting_drones
            drones_needed = field.drones_for_full_protection - current_assigned

            # If additional drones are needed and available, assign them.
            if drones_needed > 0 and available_drones:
                # Determine the center of the field.
                field_center_x = (field.left + field.right) / 2
                field_center_y = (field.top + field.bottom) / 2

                # Sort available drones by their Euclidean distance to the field center.
                available_drones.sort(
                    key=lambda d: math.sqrt(
                        (d.location.x - field_center_x) ** 2 + (d.location.y - field_center_y) ** 2
                    )
                )

                # Select the closest drones needed for full protection.
                drones_to_assign = available_drones[:drones_needed]
                for drone in drones_to_assign:
                    group_id = f"protecting {field.id}"
                    if group_id in group_ids:
                        environment.assign_group(drone, group_id)
                    else:
                        environment.assign_group(drone, "idle")
                # Remove the assigned drones from the pool.
                available_drones = available_drones[drones_needed:]

        # Finally, assign any remaining available drones to the "idle" group.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
