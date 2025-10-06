import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class DroneFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # 1. Sort fields by threat level (highest first)
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)
        if not fields:
            # No fields detected; set all drones idle.
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # The most threatened field is the first in the sorted list.
        most_threatened_field = fields[0]

        # Calculate the center of the most threatened field.
        field_center = (
            (most_threatened_field.left + most_threatened_field.right) / 2,
            (most_threatened_field.top + most_threatened_field.bottom) / 2,
        )

        # 2. Determine additional drones needed for full protection.
        # First, find drones already protecting this field.
        already_protecting = [
            drone for drone in components if drone.target == most_threatened_field.id
        ]
        # Count how many drones are currently protecting.
        current_count = len(already_protecting)
        # Calculate how many more drones are needed.
        additional_needed = max(0, most_threatened_field.drones_for_full_protection - current_count)

        # 3. The drones already protecting the field will continue in their group.
        # (Assignment below ensures consistency in group naming.)
        for drone in already_protecting:
            environment.assign_group(drone, f"protecting {most_threatened_field.id}")

        # 4. Sort the remaining drones by distance to the field center.
        remaining_drones = [drone for drone in components if drone not in already_protecting]
        remaining_drones.sort(
            key=lambda drone: math.hypot(drone.location.x - field_center[0], drone.location.y - field_center[1])
        )

        # 5. Assign as many of the closest remaining drones as necessary to protect the most threatened field.
        drones_to_assign = remaining_drones[:additional_needed]
        for drone in drones_to_assign:
            environment.assign_group(drone, f"protecting {most_threatened_field.id}")

        # Remove the drones that were just assigned.
        remaining_drones = remaining_drones[additional_needed:]

        # 6. Distribute the rest of the drones to protect the other fields.
        # If there are other fields, assign remaining drones in a round-robin fashion.
        other_fields = fields[1:]
        if other_fields:
            index = 0
            for drone in remaining_drones:
                # Cycle through the available other fields.
                field = other_fields[index % len(other_fields)]
                environment.assign_group(drone, f"protecting {field.id}")
                index += 1
        else:
            # If no other fields exist, set the remaining drones idle.
            for drone in remaining_drones:
                environment.assign_group(drone, "idle")
