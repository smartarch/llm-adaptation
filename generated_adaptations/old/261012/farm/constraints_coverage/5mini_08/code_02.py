import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that:
    - Always fully protects the single field with the highest threat_level using the closest drones.
    - Keeps drones that are already protecting that field in place.
    - Assigns additional closest drones as needed up to field.drones_for_full_protection.
    - Explicitly assigns all drones either to the protecting group for that field or to 'idle'.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute distance from a drone to the field center
        def distance_to_field_center(drone, field):
            center_x = (field.left + field.right) / 2.0
            center_y = (field.top + field.bottom) / 2.0
            dx = (drone.location.x - center_x)
            dy = (drone.location.y - center_y)
            return math.hypot(dx, dy)

        # Collect fields with positive threat
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]

        # If no threatened fields, assign everyone to idle
        if not threatened_fields:
            for c in components:
                group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, group)
            return

        # Choose the field with highest threat_level; tie-break by field.id for determinism
        # (field.id assumed to be comparable as str)
        threatened_fields_sorted = sorted(threatened_fields, key=lambda f: (-f.threat_level, str(f.id)))
        target_field = threatened_fields_sorted[0]
        protect_group = f"protecting {target_field.id}"
        if protect_group not in group_ids:
            # Fallback: if expected group name is not in group_ids, default to idle only
            for c in components:
                group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, group)
            return

        # Count drones already protecting the target field
        already_protecting = [c for c in components if c.state == "protecting" and c.target_id == target_field.id]
        num_protecting = len(already_protecting)

        # Number required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Determine how many additional drones needed (if any)
        need = max(0, required - num_protecting)

        # Build list of candidate drones not already counted in already_protecting
        already_protecting_ids = set(id(c) for c in already_protecting)
        candidates = [c for c in components if id(c) not in already_protecting_ids]

        # Sort candidates by:
        # 1) whether they are already moving to this field (prefer those)
        # 2) distance to field center (closer preferred)
        def candidate_sort_key(c):
            moving_to_same = 0 if (c.state == "moving_to_field" and c.target_id == target_field.id) else 1
            dist = distance_to_field_center(c, target_field)
            return (moving_to_same, dist)

        candidates_sorted = sorted(candidates, key=candidate_sort_key)

        # Select the needed number of candidates to send to protect the field
        selected_to_protect = candidates_sorted[:need] if need > 0 else []

        selected_to_protect_ids = set(id(c) for c in selected_to_protect)
        already_protecting_ids = set(id(c) for c in already_protecting)

        # Now assign groups for all components explicitly
        for c in components:
            cid = id(c)
            if cid in already_protecting_ids or cid in selected_to_protect_ids:
                environment.assign_group(c, protect_group)
            else:
                # assign to idle
                group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, group)