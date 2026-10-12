from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the field with the highest threat level is fully protected
        by the closest drones (including those already protecting or moving to that field).
        All other drones are assigned to 'idle'.
        """
        # Helper: distance from drone to a point
        def dist_to_point(drone, px, py):
            dx = getattr(drone.location, "x", 0) - px
            dy = getattr(drone.location, "y", 0) - py
            return hypot(dx, dy)

        # Ensure 'idle' group exists
        idle_group = "idle"
        if idle_group not in group_ids:
            # If 'idle' is not present, pick any group as safe fallback (should not happen per spec)
            fallback = group_ids[0] if group_ids else idle_group
            idle_group = fallback

        # Collect fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threatened_fields:
            # No threatened fields: assign everyone to idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Pick the field with the maximum threat_level
        target_field = max(threatened_fields, key=lambda f: f.threat_level)

        # Expected protecting group name for this field
        protect_group = f"protecting {target_field.id}"
        if protect_group not in group_ids:
            # If protecting group not available, fallback to idle for everyone
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Field center (use midpoint of bounding box)
        center_x = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        center_y = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Identify drones already protecting this field
        protecting_now = [c for c in components if getattr(c, "state", None) == "protecting"
                          and getattr(c, "target_id", None) == target_field.id]

        # Drones moving to this field
        moving_to_field = [c for c in components if getattr(c, "state", None) == "moving_to_field"
                           and getattr(c, "target_id", None) == target_field.id
                           and c not in protecting_now]

        # Other available drones (not already protecting/moving-to target)
        others = [c for c in components if c not in protecting_now and c not in moving_to_field]

        # Number of drones we still need to reach required
        current_count = len(protecting_now) + len(moving_to_field)
        need = max(0, required - current_count)

        # Sort other drones by distance to target field center
        others_sorted = sorted(others, key=lambda c: dist_to_point(c, center_x, center_y))

        # Pick nearest 'need' drones from others
        selected_from_others = others_sorted[:need] if need > 0 else []

        # Final set of drones to assign to protecting group:
        protect_set = set(protecting_now + moving_to_field + selected_from_others)

        # Assign groups: chosen -> protecting, rest -> idle
        for comp in components:
            if comp in protect_set:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, idle_group)