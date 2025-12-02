import abc
import math

try:
    from generated_adaptations.base_classes.farm import FarmAdaptation
except Exception:
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
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, p, q):
        dx = p[0] - q[0]
        dy = p[1] - q[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify fields with threat > 0 and sort by threat (desc)
        fields = [f for f in environment.fields if f.threat_level > 0]
        if not fields:
            # No threats: idle all
            for c in components:
                environment.assign_group(c, "idle")
            return

        fields.sort(key=lambda f: f.threat_level, reverse=True)

        # 2) Prepare mapping for planned groups to ensure exactly one assignment per drone
        planned = {}

        def plan(cmp, g):
            if id(cmp) in planned:
                return
            planned[id(cmp)] = g

        # 3) Top field protection
        top_field = fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            top_group = "idle"

        # Current drones protecting or en route to top field
        currently_top = [
            d for d in components
            if (d.state == "protecting" and d.target_id == top_field.id) or
               (d.state == "moving_to_field" and d.target_id == top_field.id)
        ]
        current_count = len(currently_top)
        needed = getattr(top_field, "drones_for_full_protection", 0)

        # Assign current ones to top group
        for d in currently_top:
            plan(d, top_group)

        # If not enough, pick closest from remaining drones
        if current_count < needed:
            center_top = self._field_center(top_field)
            candidates = []
            for d in components:
                if id(d) in planned:
                    continue
                pos = d.location
                candidates.append((self._dist((pos.x, pos.y), center_top), d))
            candidates.sort(key=lambda t: t[0])
            to_take = min(needed - current_count, len(candidates))
            for i in range(to_take):
                plan(candidates[i][1], top_group)

        # 4) Secondary fields (attempt to improve overall protection and reduce idle)
        # Iterate remaining fields by threat, assign drones if needed and available
        secondary_fields = [f for f in fields if f.id != top_field.id]
        for f in secondary_fields:
            group_name = f"protecting {f.id}"
            if group_name not in group_ids:
                continue

            current = [d for d in components if d.state == "protecting" and d.target_id == f.id]
            curr_count = len(current)
            target_need = getattr(f, "drones_for_full_protection", 0)

            # Plan current ones
            for d in current:
                plan(d, group_name)

            if curr_count >= target_need:
                continue

            center_f = self._field_center(f)
            available = []
            for d in components:
                if id(d) in planned:
                    continue
                dist = self._dist((d.location.x, d.location.y), center_f)
                available.append((dist, d))
            available.sort(key=lambda t: t[0])
            need_more = min(target_need - curr_count, len(available))
            for i in range(need_more):
                plan(available[i][1], group_name)

        # 5) Ensure every drone has a group (idle if not planned)
        for d in components:
            if id(d) not in planned:
                plan(d, "idle")

        # 6) Execute assignments (guarantee exactly one per drone)
        for d in components:
            environment.assign_group(d, planned[id(d)])