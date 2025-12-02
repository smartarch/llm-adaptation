from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that always fully protects the field with the highest threat level
    using the closest drones. Keeps drones that are already protecting that field in place.
    Remaining drones are set to 'idle'.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, set all drones to idle
        if not threatened_fields:
            idle_group = "idle"
            for c in components:
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
                else:
                    # fallback: assign first available group if "idle" missing (defensive)
                    environment.assign_group(c, group_ids[0] if group_ids else idle_group)
            return

        # Pick the field with the highest threat level (tie-breaker: field.id)
        top_field = max(threatened_fields, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        protect_group = f"protecting {top_field.id}"

        # Defensive: if the expected group name is not present, fall back to idle assignments
        if protect_group not in group_ids:
            for c in components:
                environment.assign_group(c, "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle"))
            return

        # Compute center of the field for distance calculations
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        # Identify drones already protecting the top field
        already_protecting = []
        others = []
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                already_protecting.append(c)
            else:
                others.append(c)

        required = int(getattr(top_field, "drones_for_full_protection", 0))
        currently_protecting = len(already_protecting)
        needed = max(0, required - currently_protecting)

        # Sort other drones by distance to the top field center
        def dist_to_field(drone):
            dx = getattr(drone.location, "x", 0) - center_x
            dy = getattr(drone.location, "y", 0) - center_y
            return math.hypot(dx, dy)

        others_sorted = sorted(others, key=dist_to_field)

        # Choose nearest drones to fill required slots
        to_assign_to_protect = set(others_sorted[:needed])

        # Assign groups: protecting top_field for chosen drones, idle for the rest
        for c in components:
            if c in already_protecting or c in to_assign_to_protect:
                environment.assign_group(c, protect_group)
            else:
                environment.assign_group(c, "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle"))