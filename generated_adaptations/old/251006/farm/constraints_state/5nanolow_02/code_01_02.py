import abc
import math

# Assuming the base class is available from the given module path
try:
    from generated_adaptations.base_classes.farm import FarmAdaptation
except Exception:
    # Fallback in case the import path differs in the execution environment
    class FarmAdaptation(abc.ABC):
        def __init__(self, **kwargs):
            super().__init__()

        @abc.abstractmethod
        def assign_drones(self, components, environment, group_ids, step: int):
            pass


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, point):
        dx = loc.x - point[0]
        dy = loc.y - point[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with threat_level > 0
        candidate_fields = [f for f in environment.fields if f.threat_level > 0]

        # If no threat, idle all drones
        if not candidate_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(candidate_fields, key=lambda f: f.threat_level)

        target_group = f"protecting {top_field.id}"

        # Ensure the target group name exists in group_ids (as per contract)
        if target_group not in group_ids:
            # If for some reason the group is not listed, fall back to "idle"
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Compute field center
        center = self._field_center(top_field)

        # Determine current protecting drones for the top field
        currently_protecting = []
        for c in components:
            if c.state == "protecting" and c.target_id == top_field.id:
                currently_protecting.append(c)

        needed = getattr(top_field, "drones_for_full_protection", 0)
        current_count = len(currently_protecting)

        # If already fully protected, keep them there, others idle
        assigned = set(currently_protecting)

        if current_count < needed:
            # Gather candidates not already protecting this field
            candidates = []
            for c in components:
                if c in assigned:
                    continue
                # Compute distance to field center
                dist = self._distance(c.location, center)
                candidates.append((dist, c))

            # Sort by distance (closest first)
            candidates.sort(key=lambda t: t[0])

            # Pick as many as needed to reach full protection
            to_assign = min(needed - current_count, len(candidates))
            for i in range(to_assign):
                _, drone = candidates[i]
                assigned.add(drone)

        # Now assign all drones in 'assigned' to the target group
        for c in components:
            if c in assigned:
                environment.assign_group(c, target_group)
            else:
                # Drones not assigned to protection stay idle
                environment.assign_group(c, "idle")