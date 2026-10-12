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
        Proactive, density-driven allocation:
        - Top-field first: fully protect the most threatened field using closest movable drones.
        - Then greedily protect other fields by threat density (threat_level / drones_for_full_protection),
          allocating the closest available movable drones to each chosen field.
        - Movable drones come from idle drones or drones on over-protected fields. Preserve persistence when possible.
        - If protection is below half, nudge the closest idle drones to the top field to raise protection.
        """
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def current_target_of(d):
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return tid
            return None

        # 1) Fields with positive threat
        fields_with_threat = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
                self._last_group[d] = "idle"
            return

        # 2) Top-field: highest threat
        fields_sorted = sorted(fields_with_threat, key=lambda fl: fl.threat_level, reverse=True)
        top_field = fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        top_center = field_center(top_field)

        # 3) Current protection for top_field (including in-transit)
        current_top = sum(1 for d in components if current_target_of(d) == top_field.id)
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # 4) Movable pool: idle drones + drones from over-protected fields
        # Current allocations per field
        env_counts = {}
        for d in components:
            tid = current_target_of(d)
            if tid is not None:
                env_counts[tid] = env_counts.get(tid, 0) + 1

        # Over-protected fields
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

        # 5) Assign to top field
        desired_group = {d: "idle" for d in components}
        to_top = min(needed_top, len(pool_top))
        for i in range(to_top):
            d = pool_top[i]
            desired_group[d] = top_group
            self._last_group[d] = top_group

        # Update counts after top allocation
        counts = dict(env_counts)
        counts[top_field.id] = current_top + to_top

        # 6) Greedy allocation to remaining fields by threat density
        # Build a pool of movable drones (idle + over-protected, excluding those already used for top)
        # We'll maintain pool_remain as those drones still available for allocation after top
        pool_remain = []
        allocated_top = set(pool_top[:to_top])
        for d in components:
            if d in allocated_top:
                continue
            # Idle drones are always movable
            if current_target_of(d) is None:
                pool_remain.append(d)
            else:
                # If the drone is on a field that's over-protected, it's movable as well
                if current_target_of(d) in over_protected:
                    pool_remain.append(d)

        # Sort pool_remain by distance to the target field center and persistence bias
        remaining_fields = fields_sorted[1:]

        # Helper to allocate drones to a specific field
        def allocate_to_field(fid, field, need, pool, counts_map):
            if need <= 0:
                return []
            center = ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)
            pool.sort(key=lambda dd: (
                dist_to_point(dd, center),
                -20 if self._last_group.get(dd) == f"protecting {fid}" else 0
            ))
            take = min(need, len(pool))
            allocated = []
            for i in range(take):
                d = pool.pop(0)
                allocated.append(d)
                desired_group[d] = f"protecting {fid}"
                self._last_group[d] = f"protecting {fid}"
                counts_map[fid] = counts_map.get(fid, 0) + 1
            return allocated

        # We'll implement a greedy loop: repeatedly pick the best field that can be fully protected
        # given the current pool_remain size.
        # We'll compute density = threat_level / drones_for_full_protection for each field.
        chosen_field_ids = set()
        while True:
            # Recompute needs for each field not yet fully protected (excluding top_field)
            candidates = []
            for f in remaining_fields:
                fid = f.id
                if fid in chosen_field_ids:
                    continue
                cur = counts.get(fid, 0)
                need = max(0, f.drones_for_full_protection - cur)
                if need > 0:
                    candidates.append((fid, f.threat_level, f.drones_for_full_protection, need, f))

            # Filter to those we can fully satisfy with current pool_remain size
            pool_size = len(pool_remain)
            feasible = [c for c in candidates if c[3] <= pool_size]
            if not feasible:
                break

            # Pick the field with max density (threat / drones_needed), tie-break by threat
            feasible.sort(key=lambda x: (x[1] / max(1, x[2]), x[1]), reverse=True)
            fid, _, _, need, field = feasible[0]
            # Allocate to this field
            allocated = allocate_to_field(fid, field, need, pool_remain, counts)
            if not allocated:
                break
            chosen_field_ids.add(fid)

        # 7) Ensure at least half are protecting if possible
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

        # 9) Apply final assignments
        for d in components:
            environment.assign_group(d, desired_group.get(d, "idle"))
            self._last_group[d] = desired_group.get(d, "idle")