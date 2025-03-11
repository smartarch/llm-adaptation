import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Build a list of free drones (those that are idle).
        free_drones = [drone for drone in components if drone.state == "idle"]

        # We will not touch drones that are already assigned (protecting or moving to field).
        # Process only fields with a threat level > 0, sorted from highest threat to lowest.
        threatened_fields = [field for field in environment.fields if field.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not threatened_fields:
            # No threat, free drones remain idle (and drones already assigned remain in their groups)
            return

        # Process the most threatened field first.
        top_field = threatened_fields[0]
        top_field_group = f"protecting {top_field.id}"

        # Count drones already protecting or en route (arriving) to the top field.
        already_protecting = top_field.protecting_drones + top_field.arriving_drones

        # Calculate additional drones needed.
        additional_needed = max(0, top_field.necessary_drones_for_full_protection - already_protecting)

        # Compute the center of the top field.
        top_center_x = (top_field.left + top_field.right) / 2
        top_center_y = (top_field.top + top_field.bottom) / 2

        # Sort free drones by their Euclidean distance to the top field's center.
        free_drones.sort(key=lambda drone: math.hypot(drone.location.x - top_center_x,
                                                      drone.location.y - top_center_y))

        # Assign as many free drones as needed to protect the top field.
        assigned_to_top = []
        for drone in free_drones:
            if additional_needed <= 0:
                break
            if top_field_group in group_ids:
                environment.assign_group(drone, top_field_group)
                assigned_to_top.append(drone)
                additional_needed -= 1

        # Remove drones assigned to the top field from free_drones.
        free_drones = [drone for drone in free_drones if drone not in assigned_to_top]

        # Now process the other threatened fields.
        for field in threatened_fields[1:]:
            field_group = f"protecting {field.id}"
            required = field.necessary_drones_for_full_protection
            already = field.protecting_drones + field.arriving_drones
            needed = max(0, required - already)

            if needed <= 0 or field_group not in group_ids:
                continue

            # Compute the center of the field.
            center_x = (field.left + field.right) / 2
            center_y = (field.top + field.bottom) / 2

            # Sort the remaining free drones by distance to this field.
            free_drones.sort(key=lambda drone: math.hypot(drone.location.x - center_x,
                                                          drone.location.y - center_y))
            assigned_to_field = []
            for drone in free_drones:
                if needed <= 0:
                    break
                environment.assign_group(drone, field_group)
                assigned_to_field.append(drone)
                needed -= 1

            # Remove these assigned drones from free_drones.
            free_drones = [drone for drone in free_drones if drone not in assigned_to_field]

        # At this point, any free drones that remain unassigned continue to be idle.
        # Since they are already idle, no further assignment is needed.
