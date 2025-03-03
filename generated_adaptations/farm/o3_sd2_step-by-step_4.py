import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # First, assign all drones to idle; we will override these assignments as needed.
        for drone in components:
            environment.assign_group(drone, "idle")

        # Filter only fields with threat > 0 and sort by threat level (high to low)
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not threatened_fields:
            return  # no threat; all drones remain idle

        # Process the most threatened field first
        top_field = threatened_fields[0]
        top_field_group = f"protecting {top_field.id}"

        # Determine how many additional drones are needed for full protection
        required_drones = top_field.necessary_drones_for_full_protection
        already_assigned = top_field.protecting_drones + top_field.arriving_drones
        additional_needed = max(0, required_drones - already_assigned)

        # Identify drones already protecting the top field; keep their assignment
        protecting_top = [drone for drone in components
                          if drone.state == "protecting" and drone.target_id == top_field.id]

        # Collect remaining drones (those not already protecting the top field)
        remaining_drones = [drone for drone in components
                            if not (drone.state == "protecting" and drone.target_id == top_field.id)]

        # Compute center of top field
        top_center_x = (top_field.left + top_field.right) / 2
        top_center_y = (top_field.top + top_field.bottom) / 2

        # Sort remaining drones by Euclidean distance to the top field's center
        remaining_drones.sort(key=lambda drone: math.hypot(drone.location.x - top_center_x,
                                                           drone.location.y - top_center_y))

        # Assign as many of the nearest drones as needed to the top field
        drones_assigned_top = []
        for drone in remaining_drones:
            if additional_needed <= 0:
                break
            environment.assign_group(drone, top_field_group)
            drones_assigned_top.append(drone)
            additional_needed -= 1

        # Remove drones assigned to the top field from the remaining list
        remaining_drones = [drone for drone in remaining_drones if drone not in drones_assigned_top]

        # For each of the other threatened fields, assign drones if needed
        for field in threatened_fields[1:]:
            field_group = f"protecting {field.id}"
            required = field.necessary_drones_for_full_protection
            already = field.protecting_drones + field.arriving_drones
            needed = max(0, required - already)

            if needed <= 0:
                continue

            # Compute the field's center
            center_x = (field.left + field.right) / 2
            center_y = (field.top + field.bottom) / 2

            # Sort the remaining drones by distance to the field's center
            remaining_drones.sort(key=lambda drone: math.hypot(drone.location.x - center_x,
                                                               drone.location.y - center_y))
            drones_assigned_field = []
            for drone in remaining_drones:
                if needed <= 0:
                    break
                environment.assign_group(drone, field_group)
                drones_assigned_field.append(drone)
                needed -= 1

            # Remove assigned drones from the remaining list
            remaining_drones = [drone for drone in remaining_drones if drone not in drones_assigned_field]

        # Any drones left remain in the idle group (already assigned as idle above)
