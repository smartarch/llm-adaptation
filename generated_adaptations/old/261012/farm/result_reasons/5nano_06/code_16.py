import math

# Assuming the base class can be imported as described
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of last group assignment for each drone (by id)
        self.prev_group = {}
        # Memory of last target field id for each drone
        self.prev_target = {}

    def _center_of_field(self, f):
        return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

    def _dist_to_point(self, drone, cx, cy):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        dx = getattr(loc, "x", 0.0) - cx
        dy = getattr(loc, "y", 0.0) - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Stage 1: Fully protect top-threat field if possible.
        Stage 2: Fully protect following-threat fields, as many as possible.
        Stage 3: Ensure at least half of drones are protecting by allocating to additional fields (up to capacity).
        Stage 4: Idle any remaining drones.
        """

        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_group[id(c)] = "idle"
                self.prev_target[id(c)] = None
            return

        # Sort fields by threat level descending
        fields_with_threat.sort(key=lambda f: f.threat_level, reverse=True)

        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        def group_for(field):
            return f"protecting {field.id}"

        # Stage 1: Top field
        top_field = fields_with_threat[0]
        top_group = group_for(top_field)
        if top_group not in group_ids:
            # If top field's group isn't valid, idle everything
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_group[id(c)] = "idle"
                self.prev_target[id(c)] = None
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        current_top = [d for d in components if self.prev_group.get(id(d)) == top_group]
        current_top_count = len(current_top)
        need_top = max(0, required_top - current_top_count)

        center_top = self._center_of_field(top_field)

        pool_top = [d for d in components if self.prev_group.get(id(d)) != top_group]

        def pool_key_top(d):
            dist = self._dist_to_point(d, center_top[0], center_top[1])
            bias_target = 0 if self.prev_target.get(id(d)) == top_field.id else 1
            return (bias_target, dist)

        pool_top_sorted = sorted(pool_top, key=pool_key_top)

        for d in pool_top_sorted[:need_top]:
            environment.assign_group(d, top_group)
            self.prev_group[id(d)] = top_group
            self.prev_target[id(d)] = top_field.id
            current_top.append(d)

        # If overshoot, demote farthest
        if len(current_top) > required_top:
            current_top_sorted = sorted(current_top,
                                        key=lambda d: self._dist_to_point(d, center_top[0], center_top[1]),
                                        reverse=True)
            to_idle = current_top_sorted[: len(current_top_sorted) - required_top]
            for d in to_idle:
                environment.assign_group(d, "idle")
                self.prev_group[id(d)] = "idle"
                self.prev_target[id(d)] = None
                current_top.remove(d)

        # Stage 2: Fully protect remaining fields in threat order, if possible
        protecting_groups = []
        for f in fields_with_threat[1:]:
            g = f"protecting {f.id}"
            if g in group_ids:
                protecting_groups.append(g)

        protecting_count = sum(
            1 for d in components if self.prev_group.get(id(d), "") in protecting_groups
        )

        if protecting_count < half_target:
            for field in fields_with_threat[1:]:
                grp = group_for(field)
                if grp not in group_ids:
                    continue

                required = int(getattr(field, "drones_for_full_protection", 0))
                current = [d for d in components if self.prev_group.get(id(d)) == grp]
                current_count = len(current)

                if current_count >= required:
                    continue

                pool = [d for d in components if self.prev_group.get(id(d)) != grp]

                center = self._center_of_field(field)

                def pool_key2(d):
                    dist = self._dist_to_point(d, center[0], center[1])
                    bias_target = 0 if self.prev_target.get(id(d)) == field.id else 1
                    return (bias_target, dist)

                pool_sorted = sorted(pool, key=pool_key2)
                needed = min(required - current_count, len(pool_sorted))

                for d in pool_sorted[:needed]:
                    environment.assign_group(d, grp)
                    self.prev_group[id(d)] = grp
                    self.prev_target[id(d)] = field.id
                    current.append(d)
                    protecting_count += 1

                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Stage 3: If still not at half, try to allocate more to other fields (respecting capacity)
        if protecting_count < half_target:
            for field in fields_with_threat[1:]:
                grp = group_for(field)
                if grp not in group_ids:
                    continue

                required = int(getattr(field, "drones_for_full_protection", 0))
                current = [d for d in components if self.prev_group.get(id(d)) == grp]
                current_count = len(current)

                if current_count >= required:
                    continue

                pool = [d for d in components if self.prev_group.get(id(d)) != grp]

                center = self._center_of_field(field)

                def pool_key3(d):
                    dist = self._dist_to_point(d, center[0], center[1])
                    bias_target = 0 if self.prev_target.get(id(d)) == field.id else 1
                    return (bias_target, dist)

                pool_sorted = sorted(pool, key=pool_key3)
                needed = min(required - current_count, len(pool_sorted))

                for d in pool_sorted[:needed]:
                    environment.assign_group(d, grp)
                    self.prev_group[id(d)] = grp
                    self.prev_target[id(d)] = field.id
                    current.append(d)
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Stage 4: idle any drones not assigned
        for d in components:
            if self.prev_group.get(id(d)) is None:
                environment.assign_group(d, "idle")
                self.prev_group[id(d)] = "idle"
                self.prev_target[id(d)] = None