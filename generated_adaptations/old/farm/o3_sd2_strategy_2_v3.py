import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields still under threat
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        threatened_field_ids = {f.id for f in threatened_fields}

        # We'll collect drones that need new assignment
        available = []

        # First, handle drones already protecting threatened fields:
        for drone in components:
            if drone.state == "protecting" and drone.target_id in threatened_field_ids:
                group = f"protecting {drone.target_id}"
                # Re-assign them to the same protecting group
                if group in group_ids:
                    environment.assign_group(drone, group)
                else:
                    environment.assign_group(drone, "idle")
            else:
                # These drones are free to be re-assigned
                available.append(drone)

        # Sort threatened fields by descending threat level
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Assign additional drones to fully protect each field
        for field in threatened_fields:
            # How many drones are already on the way or protecting?
            assigned = field.arriving_drones + field.protecting_drones
            needed = field.necessary_drones_for_full_protection - assigned
            if needed <= 0 or not available:
                continue

            # Compute field center
            cx = (field.left + field.right) / 2
            cy = (field.top + field.bottom) / 2

            # Sort available drones by distance to field center
            available.sort(key=lambda d: math.hypot(d.location.x - cx, d.location.y - cy))

            # Take the closest 'needed' drones
            to_assign = available[:needed]
            for drone in to_assign:
                group = f"protecting {field.id}"
                if group in group_ids:
                    environment.assign_group(drone, group)
                else:
                    environment.assign_group(drone, "idle")

            # Remove them from available
            available = available[needed:]

        # Any drones left get sent to idle
        for drone in available:
            environment.assign_group(drone, "idle")
