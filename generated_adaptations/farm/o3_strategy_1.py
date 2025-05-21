import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        """
        This strategy focuses on always fully protecting the field with the highest bird-threat.
        It first identifies the field with the highest threat level. Then it ensures that this field
        receives the nearest drones until it reaches full protection (i.e. until the number of drones
        protecting it equals its drones_for_full_protection). Any drones that are already assigned
        to that field are kept there, and any drones not needed for the highest-threat field are assigned
        to idle—unless they are already protecting a field that is fully secured, in which case their
        assignment is preserved.
        """
        # If there are no fields, assign all drones to idle.
        if not environment.fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # 1. Identify the field with the highest threat level.
        highest_field = max(environment.fields, key=lambda f: f.threat_level)

        # Calculate the center of the highest threat field.
        field_center_x = (highest_field.left + highest_field.right) / 2.0
        field_center_y = (highest_field.top + highest_field.bottom) / 2.0

        # 2. Determine how many drones are already protecting the highest-threat field.
        already_assigned = [drone for drone in components if drone.target == highest_field.id]
        assigned_count = len(already_assigned)

        # Compute how many additional drones are needed for full protection.
        additional_needed = highest_field.drones_for_full_protection - assigned_count
        additional_needed = max(0, additional_needed)

        # 3. For drones not already protecting the highest-threat field, sort them by distance to its center.
        def squared_distance(drone):
            dx = drone.location.x - field_center_x
            dy = drone.location.y - field_center_y
            return dx * dx + dy * dy

        available_for_assignment = [drone for drone in components if drone.target != highest_field.id]
        available_for_assignment.sort(key=squared_distance)

        # Select the closest additional_needed drones.
        selected_for_highest = available_for_assignment[:additional_needed]

        # 4. Assign groups based on the strategy.
        for drone in components:
            # Priority 1: Drones chosen (or already assigned) for highest-threat field.
            if drone in already_assigned or drone in selected_for_highest:
                group_id = f"protecting {highest_field.id}"
            else:
                # Priority 2: If the drone is already protecting a field that is fully secured, keep it there.
                if drone.target is not None:
                    field = next((f for f in environment.fields if f.id == drone.target), None)
                    if field and field.protecting_drones >= field.drones_for_full_protection:
                        group_id = f"protecting {field.id}"
                    else:
                        group_id = "idle"
                else:
                    # Priority 3: Otherwise, set the drone as idle.
                    group_id = "idle"
            environment.assign_group(drone, group_id)
