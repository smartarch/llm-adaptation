from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Find field with highest threat_level > 0.
        - Ensure it is fully protected using as many closest drones as required.
        - Keep drones already protecting or moving toward that field assigned to it.
        - Assign all other drones to 'idle'.
        """
        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute distance from drone to a point
        def distance(drone, point):
            dx = drone.location.x - point[0]
            dy = drone.location.y - point[1]
            return hypot(dx, dy)

        # Find candidate fields with threat_level > 0
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not candidate_fields:
            # No threats: assign all drones to idle
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Select the field with highest threat_level (tie-breaker: keep order)
        target_field = max(candidate_fields, key=lambda f: f.threat_level)

        # Required number of drones for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        protect_group_name = f"protecting {target_field.id}"
        idle_group_name = "idle"

        # Pre-seed drones that are already protecting or moving toward the target
        protecting_or_moving = []
        other_drones = []
        for d in components:
            if (d.state == "protecting" and d.target_id == target_field.id) or \
               (d.state == "moving_to_field" and d.target_id == target_field.id):
                protecting_or_moving.append(d)
            else:
                other_drones.append(d)

        # Start assignment set with the pre-seeded drones
        selected_for_protection = list(protecting_or_moving)

        # If we still need more drones, pick closest from other_drones
        if len(selected_for_protection) < required:
            center = field_center(target_field)
            # sort remaining drones by distance to the field center
            remaining_sorted = sorted(other_drones, key=lambda d: distance(d, center))
            needed = required - len(selected_for_protection)
            to_add = remaining_sorted[:needed]
            selected_for_protection.extend(to_add)
            # remove added drones from other_drones
            other_drones = [d for d in other_drones if d not in to_add]

        else:
            # We kept the existing protecting/moving drones; mark others as other_drones
            # (protecting_or_moving already contains them)
            other_drones = [d for d in components if d not in selected_for_protection]

        # Assign selected drones to protecting group
        # Ensure group name exists in provided group_ids (defensive)
        if protect_group_name not in group_ids:
            # Fallback: if the expected protecting group name is not present, assign all to idle
            for comp in components:
                environment.assign_group(comp, idle_group_name)
            return

        for d in selected_for_protection:
            environment.assign_group(d, protect_group_name)

        # Assign everyone else to idle (ensure idle exists)
        if idle_group_name not in group_ids:
            # If idle not present (should not happen), assign remaining to the protect group
            for d in other_drones:
                environment.assign_group(d, protect_group_name)
        else:
            for d in other_drones:
                environment.assign_group(d, idle_group_name)