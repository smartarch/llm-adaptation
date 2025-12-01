import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persisted mapping from drone -> last assigned group (for persistence)
        self._last_group = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved, time-aware, persistence-friendly allocation:
        - Fully protect the most threatened field first, using closest drones.
        - Avoid over-protecting other fields; reallocate primarily from idle or over-protected fields.
        - Bias choices toward drones that protected a field in the previous step.
        - Maintain a healthy share of drones protecting fields (>= ~50% when possible).
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
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
                self._last_group[d] = "idle"
            return

        # 2) Sort fields by threat and pick the top
        fields_sorted = sorted(fields_with_threat, key=lambda fl: fl.threat_level, reverse=True)
        top_field = fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        top_center = field_center(top_field)

        # 3) Count current protection toward top_field (including in-transit)
        current_top = 0
        for d in components:
            if current_target_of(d) == top_field.id:
                current_top += 1

        # Drones currently protecting top field; we need to fill up to drones_for_full_protection
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # 4) Prepare final desired_group mapping (default idle)
        desired_group = {d: "idle" for d in components}

        # 5) Candidate pool for top_field: idle drones + drones from over-protected fields
        # Determine over-protected fields in the environment (current allocations)
        env_counts = {}
        for d in components:
            tid = current_target_of(d)
            if tid is not None:
                env_counts[tid] = env_counts.get(tid, 0) + 1
        over_protected = set(fid for fid, cnt in env_counts.items()
                             if cnt > getattr(next((f for f in environment.fields if f.id == fid), None).drones_for_full_protection, 0))

        def dist_to_field(d, center):
            loc = getattr(d, "location", None)
            if loc is None:
                return float("inf")
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.hypot(dx, dy)

        candidates_top = []
        for d in components:
            # Skip drones already targeting the top field
            if current_target_of(d) == top_field.id:
                continue
            # Include idle drones and drones from over-protected fields
            cid = current_target_of(d)
            if cid is None or cid in over_protected:
                candidates_top.append(d)

        # Score by distance to top field, with persistence bias
        def score_top(d):
            dist = dist_to_field(d, top_center)
            bias = 0
            last = self._last_group.get(d)
            if last == top_group:
                bias = -20  # prefer staying on the same field
            return dist + bias

        candidates_top.sort(key=score_top)
        to_top = min(needed_top, len(candidates_top))
        for i in range(to_top):
            d = candidates_top[i]
            desired_group[d] = top_group
            self._last_group[d] = top_group

        # Update a rough count map for current planned allocations
        # We use final desired_group to compute how many drones are protecting each field
        field_counts = {}
        for d in components:
            grp = desired_group[d]
            if grp.startswith("protecting "):
                fid = grp[len("protecting "):]
                field_counts[fid] = field_counts.get(fid, 0) + 1

        # 6) For remaining fields, try to fully protect them in threat order
        for field in fields_sorted[1:]:
            fid = field.id
            need = max(0, field.drones_for_full_protection - field_counts.get(fid, 0))
            if need == 0:
                continue

            center = field_center(field)

            def dist_to_field(d, center=center):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center[0]
                dy = loc.y - center[1]
                return math.hypot(dx, dy)

            # Determine whom we may reallocate to this field
            # Over-protected fields in the current env
            over_env = set(fid2 for fid2, cnt in env_counts.items()
                           if cnt > getattr(next((f for f in environment.fields if f.id == fid2), None), None).drones_for_full_protection if True else False)

            # Build candidate pool: idle drones + drones from over-protected fields
            candidates = []
            for d in components:
                cur = current_target_of(d)
                if cur == fid:
                    # Already protecting this field; counted in field_counts
                    continue
                if cur is None or cur in over_env:
                    candidates.append(d)

            # Score with distance and persistence
            def score_field(d, center=center, fid=fid):
                dist = dist_to_field(d, center)
                last = self._last_group.get(d)
                pref = 0
                if last == f"protecting {fid}":
                    pref = -20
                return dist + pref

            candidates.sort(key=score_field)
            take = min(need, len(candidates))
            for i in range(take):
                d = candidates[i]
                desired_group[d] = f"protecting {fid}"
                self._last_group[d] = f"protecting {fid}"
                field_counts[fid] = field_counts.get(fid, 0) + 1

        # 7) Ensure not too many idle drones: at least half protecting if possible
        protecting_count = sum(1 for d in components if desired_group[d] != "idle")
        total = len(components)
        if total > 0 and protecting_count < total // 2:
            deficit = (total // 2) - protecting_count
            # Bring closest idle drones to top_field
            idle_drones = [d for d in components if desired_group[d] == "idle"]
            def dist_to_top_only(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - top_center[0]
                dy = loc.y - top_center[1]
                return math.hypot(dx, dy)
            idle_drones.sort(key=dist_to_top_only)
            for i in range(min(deficit, len(idle_drones))):
                d = idle_drones[i]
                desired_group[d] = top_group
                self._last_group[d] = top_group
                protecting_count += 1
                if protecting_count >= total // 2:
                    break

        # 8) Apply final assignments
        for d in components:
            environment.assign_group(d, desired_group[d])
            self._last_group[d] = desired_group[d]