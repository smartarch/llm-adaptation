import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class DroneFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # Copy the list of available drones so we can pop from it as we assign.
        available_drones = list(components)

        # Create a mapping from field id to its corresponding group id.
        # Assumes field.id is one of "Field_1", "Field_2", "Field_3", "Field_4"
        def field_group_name(field):
            return f"protecting {field.id}"

        # Sort the fields by threat level descending so that we prioritize fields under higher threat.
        fields_sorted = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # For each field, calculate how many additional drones are needed.
        for field in fields_sorted:
            # Compute the ideal number of drones required based on threat level.
            # For instance, if threat_level is 0.8 and full protection needs 5 drones,
            # we aim for ceil(0.8 * 5) drones for protection.
            ideal_drones = math.ceil(field.drones_for_full_protection * field.threat_level)
            additional_needed = max(ideal_drones - field.protecting_drones, 0)

            # Assign drones to the field as long as drones are available and the field still needs protection.
            for _ in range(additional_needed):
                if available_drones:
                    drone = available_drones.pop(0)
                    environment.assign_group(drone, field_group_name(field))
                else:
                    break

        # Any remaining drones are not needed for immediate protection; assign them to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
