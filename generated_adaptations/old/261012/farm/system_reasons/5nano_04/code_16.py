import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persisted mapping from drone -> last assigned group (for persistence)
        self._last_group = {}

    def _field_by_id(self, environment, fid):
        for f in getattr(environment, "fields", []):
            if getattr(f, "id", None) == fid:
                return f
        return None

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Greedy, proximity- and persistence-aware allocation:
        - Fully protect the top-threat field first using closest movable drones.
        - Then greedily protect other fields in decreasing threat density (threat_level / drones_for_full_protection),
          allocating the closest available movable drones to each field.
        - Movable drones are idle drones or drones currently targeting over-protected fields.
        - If protection is still under 50%, opportunistically move the closest idle drones to the top field.
        """
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def current_target_of(d):
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return tid
            return None

        # 1) Collect fields with positive threat
        fields_with_threat = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
                self._last_group[d] = "idle"
            return

        # 2) Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda fl: fl.threat_level, reverse=True)
        top_field = fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        top_center = field_center(top_field)

        # 3) Count current protection toward top_field (including in-transit)
        current_top = sum(1 for d in components if current_target_of(d) == top_field.id)
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # 4) Determine movable drones: idle or from over-protected fields
        # Current allocations per field
        env_counts = {}
        for d in components:
            tid = current_target_of(d)
            if tid is not None:
                env_counts[tid] = env_counts.get(tid, 0) + 1

        # Determine which fields are over-protected
        over_protected = set()
        for fid, cnt in env_counts.items():
            f = self._field_by_id(environment, fid)
            if f is not None and cnt > getattr(f, "drones_for_full_protection", 0):
                over_protected.add(fid)

        def dist_to_point(d, center):
            loc = getattr(d, "location", None)
            if loc is None:
                return float("inf")
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.hypot(dx, dy)

        pool_top = [
            d for d in components
            if current_target_of(d) != top_field.id and (current_target_of(d) is None or current_target_of(d) in over_protected)
        ]
        pool_top.sort(key=lambda d: dist_to_point(d, top_center))

        # Assign to top field
        to_top = min(needed_top, len(pool_top))
        desired_group = {d: "idle" for d in components}
        for i in range(to_top):
            d = pool_top[i]
            desired_group[d] = top_group
            self._last_group[d] = top_group

        # Current counts after top assignment
        counts = dict(env_counts)
        counts[top_field.id] = current_top + to_top

        # 5) Greedily allocate to remaining fields by threat density
        # threat density = threat_level / drones_for_full_protection
        remaining_fields = fields_sorted[1:]
        for f in remaining_fields:
            fid = f.id
            # how many more drones needed to fully protect this field
            cur = counts.get(fid, 0)
            need = max(0, f.drones_for_full_protection - cur)
            if need == 0:
                continue

            center = field_center(f)

            def dist_to_field(d, center=center):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center[0]
                dy = loc.y - center[1]
                return math.hypot(dx, dy)

            # Movable pool after top: remaining drones that we may reallocate
            # Recompute over_env based on current allocations to avoid breaking other fields
            over_env = set(fid2 for fid2, cnt in env_counts.items()
                           if self._field_by_id(environment, fid2) is not None
                           and cnt > getattr(self._field_by_id(environment, fid2), "drones_for_full_protection", 0))

            pool_remain = [
                d for d in components
                if desired_group[d] == "idle" and (current_target_of(d) is None or current_target_of(d) in over_env)
            ]
            # Include also any drones in over-protected fields not yet assigned this step
            pool_remain.extend([
                d for d in components
                if current_target_of(d) in over_env and desired_group[d] == "idle"
            ])
            pool_remain = list(set(pool_remain))  # unique
            # Bias toward drones that protected this field in the last step
            pool_remain.sort(key=lambda d: (
                dist_to_field(d),
                -1 if self._last_group.get(d) == f"protecting {fid}" else 0
            ))

            take = min(need, len(pool_remain))
            for i in range(take):
                d = pool_remain[i]
                desired_group[d] = f"protecting {fid}"
                self._last_group[d] = f"protecting {fid}"
                counts[fid] = counts.get(fid, 0) + 1

        # 6) Ensure at least half are protecting if possible
        protecting_count = sum(1 for d in components if desired_group[d] != "idle")
        total = len(components)
        if total > 0 and protecting_count < total // 2:
            deficit = (total // 2) - protecting_count
            idle_drones = [d for d in components if desired_group[d] == "idle"]
            idle_drones.sort(key=lambda dd: dist_to_point(dd, top_center))
            for i in range(min(deficit, len(idle_drones))):
                d = idle_drones[i]
                desired_group[d] = top_group
                self._last_group[d] = top_group
                protecting_count += 1
                if protecting_count >= total // 2:
                    break

        # 7) Apply final assignments
        for d in components:
            environment.assign_group(d, desired_group.get(d, "idle"))
            self._last_group[d] = desired_group.get(d, "idle")