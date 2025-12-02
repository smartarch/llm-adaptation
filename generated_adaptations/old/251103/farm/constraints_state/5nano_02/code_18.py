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

        # 1) Identify threatened fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort threat fields by threat level (high to low) and pick top
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_id = top_field.id

        # 3) Compute need for top field (ignore moving_to_field in need calculation)
        eff_prot = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        full_needed = getattr(top_field, "drones_for_full_protection", 0)
        need = max(0, full_needed - eff_prot)

        # Reinforcements: list of (dist, drone)
        reinforcements = []

        if need > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Drones already on top (protecting or en route to top)
            on_top = set()
            for d in components:
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id:
                    on_top.add(d)
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                    on_top.add(d)

            # Idle candidates not currently on top
            idle_candidates = []
            for d in components:
                if d in on_top:
                    continue
                if getattr(d, "state", None) == "idle":
                    loc = getattr(d, "location", None)
                    dist = float('inf')
                    if loc is not None:
                        dist = math.hypot(loc.x - cx, loc.y - cy)
                    idle_candidates.append((dist, d))

            idle_candidates.sort(key=lambda t: t[0])
            # Take as many idle drones as possible up to 'need'
            take_idle = min(need, len(idle_candidates))
            for i in range(take_idle):
                reinforcements.append((idle_candidates[i][0], idle_candidates[i][1]))

            remaining = need - take_idle
            if remaining > 0:
                # Consider other drones (not on top) to fill the remaining need
                other_candidates = []
                for d in components:
                    if d in on_top:
                        continue
                    if getattr(d, "state", None) == "idle":
                        # Already handled by idle pool; skip
                        continue
                    loc = getattr(d, "location", None)
                    dist = float('inf')
                    if loc is not None:
                        dist = math.hypot(loc.x - cx, loc.y - cy)
                    other_candidates.append((dist, d))

                other_candidates.sort(key=lambda t: t[0])
                for i in range(min(remaining, len(other_candidates))):
                    reinforcements.append((other_candidates[i][0], other_candidates[i][1]))

        # 4) Cap to avoid overprotection of top field
        # Allowed number of reinforcements to top
        allowed_reinforcements = max(0, full_needed - eff_prot)
        if len(reinforcements) > allowed_reinforcements:
            # Remove the farthest drones first
            reinforcements.sort(key=lambda t: t[0], reverse=True)  # sort by distance desc
            to_drop = len(reinforcements) - allowed_reinforcements
            reinforcements = reinforcements[:-to_drop]  # drop the farthest ones
        # Build a set for quick lookup
        reinforcement_set = set(d for _, d in reinforcements)

        # 5) Apply reinforcement assignments
        top_group = f"protecting {top_id}"
        for d in reinforcement_set:
            safe = self._safe_group(top_group, valid_groups)
            if safe:
                environment.assign_group(d, safe)
            else:
                environment.assign_group(d, "idle")

        # 6) Map the rest of the drones
        # Recompute counts with reinforcements considered toward top
        counts = {f.id: getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0) for f in threat_fields}
        if top_id in counts:
            counts[top_id] += len(reinforcement_set)
        # Build field limits
        limits = {f.id: getattr(f, "drones_for_full_protection", 0) for f in threat_fields}

        for d in components:
            if d in reinforcement_set:
                continue  # already assigned to top

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
                # Idle or other transient states
                if "idle" in valid_groups:
                    environment.assign_group(d, "idle")
                else:
                    # Fallback: try to map to top field group if possible
                    top_group = f"protecting {top_id}"
                    safe = self._safe_group(top_group, valid_groups)
                    if safe:
                        environment.assign_group(d, safe)
                    else:
                        environment.assign_group(d, "idle")