import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: sort fields by threat level descending, ignoring fields with no threat.
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # If no fields are under threat, assign all drones to idle.
        if not threatened_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Keep track of which drones are already assigned.
        assigned_drones = set()

        # Step 2: Handle the most threatened field first.
        highest_field = threatened_fields[0]
        # Compute field center (using sensor boundaries).
        center_x = (highest_field.left + highest_field.right) / 2.0
        center_y = (highest_field.top + highest_field.bottom) / 2.0

        # Identify drones already protecting this field.
        drones_currently_for_high = [d for d in components if d.target_id == highest_field.id]
        for drone in drones_currently_for_high:
            environment.assign_group(drone, f"protecting {highest_field.id}")
            assigned_drones.add(drone)

        # Determine additional drones needed.
        current_count = highest_field.protecting_drones + highest_field.arriving_drones
        additional_needed = max(0, highest_field.drones_for_full_protection - current_count)
        # Adjust additional_needed by subtracting drones already assigned (if any).
        additional_needed = max(0, additional_needed - len(drones_currently_for_high))

        # Find drones not already assigned.
        remaining_drones = [d for d in components if d not in assigned_drones]
        # Sort by distance to the highest field center.
        remaining_drones.sort(key=lambda d: math.hypot(d.location.x - center_x, d.location.y - center_y))

        # Assign additional drones for highest field.
        for drone in remaining_drones[:additional_needed]:
            environment.assign_group(drone, f"protecting {highest_field.id}")
            assigned_drones.add(drone)
        # Remove the ones we just assigned.
        remaining_drones = [d for d in remaining_drones if d not in assigned_drones]

        # Step 6: Distribute the remaining drones to the other threatened fields.
        for field in threatened_fields[1:]:
            # Determine center of the field.
            field_center_x = (field.left + field.right) / 2.0
            field_center_y = (field.top + field.bottom) / 2.0
            # Identify drones already protecting this field (if any).
            already_assigned = [d for d in remaining_drones if d.target_id == field.id]
            # Calculate additional drones needed for full protection.
            current_field_count = field.protecting_drones + field.arriving_drones + len(already_assigned)
            needed = max(0, field.drones_for_full_protection - current_field_count)

            # First, assign the drones already targeting this field.
            for drone in already_assigned:
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_drones.add(drone)
            # Remove already assigned drones.
            remaining_drones = [d for d in remaining_drones if d not in already_assigned]

            # Sort the remaining drones by their distance to this field's center.
            remaining_drones.sort(key=lambda d: math.hypot(d.location.x - field_center_x, d.location.y - field_center_y))
            # Assign as many drones as needed.
            for drone in remaining_drones[:needed]:
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_drones.add(drone)
            remaining_drones = [d for d in remaining_drones if d not in assigned_drones]

        # Step 7: Any drones left unassigned are set to idle.
        for drone in components:
            if drone not in assigned_drones:
                environment.assign_group(drone, "idle")
