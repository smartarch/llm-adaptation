from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the single field with highest threat_level > 0
        is fully protected using the closest drones. All other drones are set to idle.
        """
        # Helper: compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: euclidean distance between drone and a point
        def distance(drone, point):
            dx = (drone.location.x - point[0])
            dy = (drone.location.y - point[1])
            return math.hypot(dx, dy)

        # Build list of fields with positive threat
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        idle_group = "idle"
        if not candidate_fields:
            for comp in components:
                # ensure idle group exists in group_ids
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    # fallback: assign first group if idle not available
                    environment.assign_group(comp, group_ids[0] if group_ids else idle_group)
            return

        # Pick the field with highest threat_level; deterministic tie-break by id
        candidate_fields.sort(key=lambda f: (-f.threat_level, f.id))
        target_field = candidate_fields[0]
        protecting_group = f"protecting {target_field.id}"
        # Ensure group exists; if not, fall back to idle for all
        if protecting_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, idle_group if idle_group in group_ids else group_ids[0])
            return

        # Count current protecting and arriving drones towards this field (based on snapshot attributes)
        protecting_count = 0
        arriving_count = 0
        for comp in components:
            if comp.target_id == target_field.id:
                if getattr(comp, "state", "") == "protecting":
                    protecting_count += 1
                elif getattr(comp, "state", "") == "moving_to_field":
                    arriving_count += 1

        # Determine how many drones are required for full protection
        required_total = int(getattr(target_field, "drones_for_full_protection", 0))
        # remaining drones to assign (beyond those already protecting or arriving)
        remaining_needed = max(0, required_total - (protecting_count + arriving_count))

        # Prepare list of candidate drones to reassign (those not already targeting this field)
        other_drones = []
        for comp in components:
            if comp.target_id != target_field.id:
                # compute distance to field center for sorting
                other_drones.append((distance(comp, field_center(target_field)), comp))

        # Sort by distance (closest first)
        other_drones.sort(key=lambda pair: pair[0])

        # Select closest drones to fill the remaining_needed
        selected_for_protection = set()
        for i in range(min(remaining_needed, len(other_drones))):
            selected_for_protection.add(other_drones[i][1])

        # Now assign groups to every drone explicitly
        for comp in components:
            # If drone already targeting the chosen field (protecting or moving), keep it assigned to protecting group
            if comp.target_id == target_field.id:
                environment.assign_group(comp, protecting_group)
            # Else if selected as one of the closest to send, assign to protecting group
            elif comp in selected_for_protection:
                environment.assign_group(comp, protecting_group)
            else:
                # Otherwise assign to idle
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    # fallback to any valid group (choose first)
                    environment.assign_group(comp, group_ids[0] if group_ids else protecting_group)