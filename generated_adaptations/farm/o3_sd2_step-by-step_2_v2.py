import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Get all fields with a threat (threat_level > 0) and sort them from highest to lowest.
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        if not threatened_fields:
            # If no fields are under threat, assign all drones to "idle".
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        main_field = threatened_fields[0]

        # Calculate center of the most threatened field.
        main_center_x = (main_field.left + main_field.right) / 2.0
        main_center_y = (main_field.top + main_field.bottom) / 2.0

        # Step 2: Determine how many additional drones are needed for full protection.
        # Combine the counts of protecting and arriving drones.
        already_assigned_main = main_field.protecting_drones + main_field.arriving_drones
        additional_needed_main = max(main_field.necessary_drones_for_full_protection - already_assigned_main, 0)

        # Step 3: Identify drones already assigned to the main field.
        # This now includes both drones that are currently "protecting" and those "moving to field".
        already_assigned_drones = [drone for drone in components
                                   if drone.state in ("protecting", "moving to field") and drone.target_id == main_field.id]
        for drone in already_assigned_drones:
            environment.assign_group(drone, f"protecting {main_field.id}")

        # Keep track of drones that have been assigned.
        assigned_drones = set(already_assigned_drones)
        # The remaining drones that have not yet been assigned.
        remaining_drones = [drone for drone in components if drone not in assigned_drones]

        # Step 4: Sort the remaining drones by distance to the main field center.
        def distance_to_main(drone):
            dx = drone.location.x - main_center_x
            dy = drone.location.y - main_center_y
            return dx * dx + dy * dy  # squared Euclidean distance

        remaining_drones.sort(key=distance_to_main)

        # Step 5: Assign as many of the nearest remaining drones as necessary to protect the main field.
        for drone in remaining_drones[:]:
            if additional_needed_main > 0:
                environment.assign_group(drone, f"protecting {main_field.id}")
                assigned_drones.add(drone)
                remaining_drones.remove(drone)
                additional_needed_main -= 1
            else:
                break

        # Step 6: For the other threatened fields, distribute remaining drones.
        # Iterate over fields (excluding the main field) and assign drones based on the additional number needed.
        for field in threatened_fields[1:]:
            # Calculate field center.
            center_x = (field.left + field.right) / 2.0
            center_y = (field.top + field.bottom) / 2.0
            # Determine how many additional drones are needed.
            already_assigned_field = field.protecting_drones + field.arriving_drones
            additional_needed_field = max(field.necessary_drones_for_full_protection - already_assigned_field, 0)
            if additional_needed_field <= 0:
                continue

            # Sort remaining drones by distance to this field.
            remaining_drones.sort(key=lambda d: (d.location.x - center_x)**2 + (d.location.y - center_y)**2)
            for drone in remaining_drones[:]:
                if additional_needed_field > 0:
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_drones.add(drone)
                    remaining_drones.remove(drone)
                    additional_needed_field -= 1
                else:
                    break

        # Step 7: Assign all remaining drones to the "idle" group.
        for drone in remaining_drones:
            environment.assign_group(drone, "idle")
