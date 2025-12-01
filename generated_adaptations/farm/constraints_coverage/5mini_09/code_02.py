from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: return group name for protecting a field
        def protecting_group_name(field_id):
            return f"protecting {field_id}"

        idle_group = "idle"
        # Safety: ensure idle is present in group_ids
        if idle_group not in group_ids:
            # If idle isn't valid (shouldn't happen), fall back to first group
            idle_group = group_ids[0] if group_ids else idle_group

        # Filter fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for drone in components:
                environment.assign_group(drone, idle_group)
            return

        # Choose the field with the highest threat_level (tie broken by original order)
        top_field = max(threatened_fields, key=lambda f: f.threat_level)

        protect_group = protecting_group_name(top_field.id)
        if protect_group not in group_ids:
            # In case the expected protect group is not present, fallback to idle for safety
            protect_group = idle_group

        # Compute field center for distance calculations
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        # Drones already assigned to this field (either moving to it or protecting it)
        already_assigned = [d for d in components if getattr(d, "target_id", None) == top_field.id]

        required = int(getattr(top_field, "drones_for_full_protection", 0))
        # Number still needed
        needed = max(0, required - len(already_assigned))

        # Candidates: drones not already assigned to this field
        candidates = [d for d in components if d not in already_assigned]

        # Sort candidates by squared distance to field center (closest first)
        def sq_dist(drone):
            lx = getattr(drone.location, "x", 0)
            ly = getattr(drone.location, "y", 0)
            dx = lx - center_x
            dy = ly - center_y
            return dx * dx + dy * dy

        candidates.sort(key=sq_dist)

        # Select the closest 'needed' drones (or fewer if not enough)
        selected = candidates[:needed] if needed > 0 else []

        # Build final set of drones that should be assigned to protecting this field
        protect_set = set(already_assigned + selected)

        # Assign groups to all drones: protect_set -> protecting group, others -> idle
        for drone in components:
            if drone in protect_set:
                environment.assign_group(drone, protect_group)
            else:
                environment.assign_group(drone, idle_group)