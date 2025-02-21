import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmDroneAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        # Get fields sorted by threat level (highest first)
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)

        # List of available drones (excluding those already assigned to protect fully covered fields)
        available_drones = list(components)

        # Dictionary to track how many drones are assigned per field
        assigned_drones = {field.id: field.protecting_drones for field in fields}

        for field in fields:
            required_drones = field.necessary_drones_for_full_protection - assigned_drones[field.id]

            if required_drones > 0:
                # Sort available drones by distance to the field (closest first)
                available_drones.sort(key=lambda drone: self._distance(drone.location, field))

                # Assign required number of drones to this field
                for _ in range(required_drones):
                    if available_drones:
                        drone = available_drones.pop(0)
                        environment.assign_group(drone, f"protecting {field.id}")
                        assigned_drones[field.id] += 1
                    else:
                        break  # No more available drones

        # Remaining drones stay idle
        for drone in available_drones:
            environment.assign_group(drone, "idle")

    def _distance(self, location, field):
        """Calculate the Manhattan distance between the drone and the field center."""
        field_center_x = (field.left + field.right) / 2
        field_center_y = (field.top + field.bottom) / 2
        return abs(location.x - field_center_x) + abs(location.y - field_center_y)
