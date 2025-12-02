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

        # Prepare mapping for field groups and assignment plan
        assign_map = {}  # key: id(component) -> (component, group_name)

        def plan_assign(cmp, group_name):
            assign_map[id(cmp)] = (cmp, group_name)

        # If no threat, idle all drones
        if not candidate_fields:
            for c in components:
                plan_assign(c, "idle")

        else:
            # Prepare field ordering by threat level
            candidate_fields.sort(key=lambda f: f.threat_level, reverse=True)
            top_field = candidate_fields[0]
            top_group = f"protecting {top_field.id}"
            if top_group not in group_ids:
                top_group = "idle"

            # Centers for distance calculations
            centers = {f.id: self._field_center(f) for f in candidate_fields}

            # Current protecting drones for top field (from current state)
            currently_protecting = [
                c for c in components if c.state == "protecting" and c.target_id == top_field.id
            ]
            current_count = len(currently_protecting)
            needed = getattr(top_field, "drones_for_full_protection", 0)

            # Assign currently protecting drones to the top group
            for c in currently_protecting:
                plan_assign(c, top_group)

            # If not enough, pick closest available drones
            if current_count < needed:
                # Build available list sorted by distance to top field center
                center_top = centers[top_field.id]
                available = []
                for c in components:
                    if id(c) in assign_map:
                        continue
                    dist = self._distance(c.location, center_top)
                    available.append((dist, c))
                available.sort(key=lambda t: t[0])
                to_take = min(needed - current_count, len(available))
                for i in range(to_take):
                    _, drone = available[i]
                    plan_assign(drone, top_group)

            # Remaining fields: try to assign protection up to their drones_for_full_protection
            remaining_fields = [f for f in candidate_fields if f.id != top_field.id]
            for f in remaining_fields:
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    # If the group isn't defined, skip planning this field
                    continue

                current = [c for c in components if c.state == "protecting" and c.target_id == f.id]
                curr_count = len(current)
                target_need = getattr(f, "drones_for_full_protection", 0)

                # Plan current ones to this group
                for c in current:
                    plan_assign(c, group_name)

                if curr_count >= target_need:
                    continue

                # Gather available drones not yet assigned
                center_f = centers.get(f.id, self._field_center(f))
                available = []
                for c in components:
                    if id(c) in assign_map:
                        continue
                    dist = self._distance(c.location, center_f)
                    available.append((dist, c))
                available.sort(key=lambda t: t[0])
                needed_more = min(target_need - curr_count, len(available))
                for i in range(needed_more):
                    _, drone = available[i]
                    plan_assign(drone, group_name)

            # Finally, any drone not assigned goes to idle
            for c in components:
                if id(c) not in assign_map:
                    plan_assign(c, "idle")

        # Execute the planned groups, ensuring each component is assigned exactly once
        for c in components:
            if id(c) in assign_map:
                _, group_name = assign_map[id(c)]
                environment.assign_group(c, group_name)
            else:
                environment.assign_group(c, "idle")