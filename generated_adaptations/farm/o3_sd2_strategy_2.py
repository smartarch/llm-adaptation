import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Create a set of unassigned drones.
        available_drones = list(components)

        # For fields with threat level > 0, sort them by descending threat level.
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        threatened_fields.sort(key=lambda field: field.threat_level, reverse=True)

        # Process each threatened field in order.
        for field in threatened_fields:
            # Calculate additional drones required.
            current_drones = field.arriving_drones + field.protecting_drones
            drones_needed = field.necessary_drones_for_full_protection - current_drones

            # Only assign if additional drones are needed.
            if drones_needed > 0 and available_drones:
                # Calculate the field's center for distance computations.
                field_center_x = (field.left + field.right) / 2
                field_center_y = (field.top + field.bottom) / 2

                # Sort available drones by Euclidean distance to the field center.
                available_drones.sort(
                    key=lambda d: math.sqrt(
                        (d.location.x - field_center_x) ** 2 + (d.location.y - field_center_y) ** 2
                    )
                )

                # Take the closest drones needed.
                drones_to_assign = available_drones[:drones_needed]
                for drone in drones_to_assign:
                    group_id = f"protecting {field.id}"
                    if group_id in group_ids:
                        environment.assign_group(drone, group_id)
                    else:
                        # Fallback: if the computed group_id is not in the provided group_ids, assign idle.
                        environment.assign_group(drone, "idle")
                # Remove assigned drones from available pool.
                available_drones = available_drones[drones_needed:]

        # Assign any remaining drones to the "idle" group.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
