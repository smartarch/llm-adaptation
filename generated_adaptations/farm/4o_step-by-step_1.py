import abc
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmDroneAssignment(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # Retrieve field information
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # Map field IDs to the required group names
        field_groups = {f"idle": "idle"}
        for field in fields:
            field_groups[field.id] = f"protecting {field.id}"

        # Initialize list for drones
        available_drones = list(components)

        # Assign drones to the most threatened field first
        for field in fields:
            required_drones = field.necessary_drones_for_full_protection - field.protecting_drones
            if required_drones > 0:
                # Get drones currently protecting this field
                current_drones = [d for d in available_drones if d.target == field.id]
                needed_additional_drones = max(0, required_drones - len(current_drones))

                # Sort remaining drones by distance to this field
                remaining_drones = [d for d in available_drones if d.target != field.id]
                remaining_drones.sort(key=lambda d: self.distance(d.location, field))

                # Assign current and additional needed drones to the field
                for drone in current_drones:
                    environment.assign_group(drone, field_groups[field.id])
                    available_drones.remove(drone)

                for i in range(min(needed_additional_drones, len(remaining_drones))):
                    environment.assign_group(remaining_drones[i], field_groups[field.id])
                    available_drones.remove(remaining_drones[i])

        # Assign remaining drones to the next most threatened fields
        for field in fields:
            if not available_drones:
                break
            environment.assign_group(available_drones.pop(0), field_groups[field.id])

        # Any remaining drones remain idle
        for drone in available_drones:
            environment.assign_group(drone, field_groups["idle"])

    def distance(self, location, field):
        """Compute Euclidean distance from drone location to field center."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return math.sqrt((location.x - field_center_x) ** 2 + (location.y - field_center_y) ** 2)
