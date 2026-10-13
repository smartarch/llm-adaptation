import abc
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assign = {}
        self.same_count = {}
        self.total_count = {}

    def _dist_to_field(self, drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = drone.location.x - cx
        dy = drone.location.y - cy
        return (dx * dx + dy * dy) ** 0.5

    def _select_for_field(self, remaining, field, n):
        if n <= 0 or not remaining:
            return []
        field_group = f"protecting {field.id}"

        def dist(c):
            return self._dist_to_field(c, field)

        prev = [c for c in remaining if self.prev_assign.get(id(c)) == field_group]
        other = [c for c in remaining if self.prev_assign.get(id(c)) != field_group]
        prev.sort(key=dist)
        other.sort(key=dist)

        selected = prev[:n]
        if len(selected) < n:
            selected.extend(other[:n - len(selected)])
        return selected

    def assign_drones(self, components, environment, group_ids, step):
        group_ids_set = set(group_ids)

        # Initialize previous assignments from component target_id if not tracked yet
        for c in components:
            cid = id(c)
            if cid not in self.prev_assign:
                if c.target_id is not None:
                    self.prev_assign[cid] = f"protecting {c.target_id}"
                else:
                    self.prev_assign[cid] = "idle"

        # Identify threatened fields that have a valid protection group
        threatened = []
        for f in environment.fields:
            if f.threat_level > 0:
                g = f"protecting {f.id}"
                if g in group_ids_set:
                    threatened.append((f, g))
        threatened.sort(key=lambda x: (-x[0].threat_level, str(x[0].id)))

        assignments = {}

        if not threatened:
            idle_group = "idle" if "idle" in group_ids_set else group_ids[0]
            for c in components:
                assignments[id(c)] = idle_group
        else:
            # 1. Fully protect the most threatened field with its closest drones
            top_field, top_group = threatened[0]
            top_cap = top_field.drones_for_full_protection
            if top_cap > 0:
                sorted_comps = sorted(components, key=lambda c: self._dist_to_field(c, top_field))
                top_drones = sorted_comps[:top_cap]
            else:
                top_drones = []
            top_ids = {id(c) for c in top_drones}
            for c in top_drones:
                assignments[id(c)] = top_group
            remaining = [c for c in components if id(c) not in top_ids]

            skipped = []
            # 2. Fully protect other fields if enough remaining drones
            for field, group in threatened[1:]:
                cap = field.drones_for_full_protection
                if cap <= 0:
                    continue
                if len(remaining) >= cap:
                    selected = self._select_for_field(remaining, field, cap)
                    for c in selected:
                        assignments[id(c)] = group
                    sel_ids = {id(c) for c in selected}
                    remaining = [c for c in remaining if id(c) not in sel_ids]
                else:
                    skipped.append((field, group))

            used = len(components) - len(remaining)
            total = len(components)
            half = total / 2.0

            # 3. If too many idle, partially protect skipped fields to reach at least half utilization
            if used < half and remaining:
                for field, group in skipped:
                    cap = field.drones_for_full_protection
                    if cap <= 0:
                        continue
                    need = int(half - used + 0.999)  # ceil
                    if need <= 0:
                        break
                    n = min(len(remaining), cap, need)
                    if n <= 0:
                        continue
                    selected = self._select_for_field(remaining, field, n)
                    for c in selected:
                        assignments[id(c)] = group
                    sel_ids = {id(c) for c in selected}
                    remaining = [c for c in remaining if id(c) not in sel_ids]
                    used += len(selected)
                    if used >= half:
                        break

            # 4. Remaining drones go idle
            idle_group = "idle" if "idle" in group_ids_set else group_ids[0]
            for c in remaining:
                assignments[id(c)] = idle_group

        # Ensure every component has a valid assignment
        idle_group = "idle" if "idle" in group_ids_set else group_ids[0]
        for c in components:
            cid = id(c)
            if cid not in assignments or assignments[cid] not in group_ids_set:
                assignments[cid] = idle_group

        # Apply assignments and update internal state
        for c in components:
            group = assignments[id(c)]
            environment.assign_group(c, group)

            cid = id(c)
            old_group = self.prev_assign.get(cid)
            if old_group == group:
                self.same_count[cid] = self.same_count.get(cid, 0) + 1
            else:
                self.same_count[cid] = 0
            self.total_count[cid] = self.total_count.get(cid, 0) + 1
            self.prev_assign[cid] = group