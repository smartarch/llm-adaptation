import math
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _safe_group(self, group_name, valid_groups):
        if group_name in valid_groups:
            return group_name
        if "idle" in valid_groups:
            return "idle"
        return None

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)

        # 1) Threat assessment: identify fields with any threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (high to low)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_id = top_field.id

        # 2) Compute need for top field (ignore moving_to_field when calculating need)
        top_current = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        full_top = getattr(top_field, "drones_for_full_protection", 0)
        need_top = max(0, full_top - top_current)

        # Centers for distance calculations
        top_cx = (top_field.left + top_field.right) / 2.0
        top_cy = (top_field.top + top_field.bottom) / 2.0

        # 3) Identify potential reinforcements for the top field (prefer idle drones)
        on_top = set()
        for d in components:
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id:
                on_top.add(d)
            if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                on_top.add(d)

        idle_candidates = []
        for d in components:
            if d in on_top:
                continue
            if getattr(d, "state", None) == "idle":
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - top_cx, loc.y - top_cy)
                idle_candidates.append((dist, d))
        idle_candidates.sort(key=lambda t: t[0])

        rein_top = []
        if need_top > 0 and idle_candidates:
            take = min(need_top, len(idle_candidates))
            rein_top = [d for _, d in idle_candidates[:take]]

        # 4) Optional reinforcement for second-highest field if there is idle surplus
        second_field = threat_fields[1] if len(threat_fields) > 1 else None
        rein_second = []
        if second_field is not None and rein_top:
            # compute how many extra can go to second (cap by its need)
            second_id = second_field.id
            second_current = getattr(second_field, "protecting_drones", 0) + getattr(second_field, "arriving_drones", 0)
            second_full = getattr(second_field, "drones_for_full_protection", 0)
            need_second = max(0, second_full - second_current)

            # gather remaining idle drones (not already used for top)
            used_for_top = set(rein_top)
            idle_remaining = []
            for d in idle_candidates:
                if d in used_for_top:
                    continue
                dist = idle_candidates  # existing dist value; recompute for safety
                # compute distance to second field center
                scx = (second_field.left + second_field.right) / 2.0
                scy = (second_field.top + second_field.bottom) / 2.0
                loc = getattr(d, "location", None)
                dist_to_second = float("inf")
                if loc is not None:
                    dist_to_second = math.hypot(loc.x - scx, loc.y - scy)
                idle_remaining.append((dist_to_second, d))
            idle_remaining.sort(key=lambda t: t[0])

            if need_second > 0 and idle_remaining:
                take2 = min(need_second, len(idle_remaining))
                rein_second = [d for _, d in idle_remaining[:take2]]

        # 5) Apply reinforcements with proper cap
        # Cap tops to not exceed full_top
        counts_top = top_current
        if rein_top:
            # ensure not exceeding
            max_add_top = max(0, full_top - top_current)
            if len(rein_top) > max_add_top:
                rein_top = rein_top[:max_add_top]
        # Prepare final sets
        reinforcement_top_set = set(rein_top)
        reinforcement_second_set = set(rein_second)

        # Update environment with reinforcements
        top_group = f"protecting {top_id}"
        for d in reinforcement_top_set:
            safe = self._safe_group(top_group, valid_groups)
            if safe:
                environment.assign_group(d, safe)
            else:
                environment.assign_group(d, "idle")

        # For second field reinforcements, ensure we don't exceed its capacity
        second_group = f"protecting {second_field.id}" if second_field is not None else None
        # Compute current counts including reinforcements
        counts = {f.id: getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0) for f in threat_fields}
        if top_id in counts:
            counts[top_id] += len(reinforcement_top_set)
        if second_field is not None and second_field.id in counts:
            counts[second_field.id] += len(reinforcement_second_set)

        # Cap second field reinforcement
        if reinforcement_second_set and second_field is not None:
            limit2 = getattr(second_field, "drones_for_full_protection", 0)
            current2 = counts.get(second_field.id, 0)
            # If would exceed, trim the reinforcements from farthest (approx by distance among reinfor_second)
            if current2 > limit2:
                over = current2 - limit2
                # simply drop up to 'over' drones from reinforcement_second_set (best effort)
                if over > 0:
                    to_drop = min(over, len(reinforcement_second_set))
                    # remove arbitrary drones to drop
                    for i, d in enumerate(list(reinforcement_second_set)):
                        if i < to_drop:
                            reinforcement_second_set.remove(d)
                    # no need to re-assign dropped drones; they'll be handled below

        for d in reinforcement_second_set:
            if second_field is None:
                break
            safe = self._safe_group(second_group, valid_groups)
            if safe:
                environment.assign_group(d, safe)
            else:
                environment.assign_group(d, "idle")

        # 6) Map the rest of the drones, minimizing thrash and respecting protection caps
        # Recompute counts after reinforcements
        counts = {f.id: getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0) for f in threat_fields}
        if top_field is not None:
            counts[top_id] = counts.get(top_id, 0) + len(reinforcement_top_set)
        if second_field is not None:
            counts[second_field.id] = counts.get(second_field.id, 0) + len(reinforcement_second_set)

        limits = {f.id: getattr(f, "drones_for_full_protection", 0) for f in threat_fields}

        for d in components:
            if d in reinforcement_top_set or d in reinforcement_second_set:
                continue  # already assigned

            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)

            if st == "protecting" and tid is not None:
                limit = limits.get(tid, 0)
                if counts.get(tid, 0) < limit:
                    grp = f"protecting {tid}"
                    safe = self._safe_group(grp, valid_groups)
                    if safe:
                        environment.assign_group(d, safe)
                        counts[tid] = counts.get(tid, 0) + 1
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")
            elif st == "moving_to_field" and tid is not None:
                limit = limits.get(tid, 0)
                if counts.get(tid, 0) < limit:
                    grp = f"protecting {tid}"
                    safe = self._safe_group(grp, valid_groups)
                    if safe:
                        environment.assign_group(d, safe)
                        counts[tid] = counts.get(tid, 0) + 1
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")
            else:
                # Idle or other, prefer idle if available
                if "idle" in valid_groups:
                    environment.assign_group(d, "idle")
                else:
                    # Fallback: try to map to the top field if possible
                    top_group = f"protecting {top_id}"
                    safe = self._safe_group(top_group, valid_groups)
                    if safe:
                        # Only assign to top if it won't exceed protection
                        if counts.get(top_id, 0) < limits.get(top_id, 0):
                            environment.assign_group(d, safe)
                            counts[top_id] = counts.get(top_id, 0) + 1
                        else:
                            environment.assign_group(d, "idle")
                    else:
                        environment.assign_group(d, "idle")