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

        # Identify threatened fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (high to low)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_id = top_field.id

        # Compute need for top field (ignore moving_to_field when calculating needs)
        eff_prot = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        full_needed = getattr(top_field, "drones_for_full_protection", 0)
        need = max(0, full_needed - eff_prot)

        reinforcements = set()

        if need > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Drones currently on top (protecting or en route to top)
            on_top = set()
            for d in components:
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id:
                    on_top.add(d)
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                    on_top.add(d)

            # Candidates to reinforce (exclude those already on top)
            idle_candidates = []
            other_candidates = []
            for d in components:
                if d in on_top:
                    continue
                loc = getattr(d, "location", None)
                dist = float('inf')
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                if getattr(d, "state", None) == "idle":
                    idle_candidates.append((dist, d))
                else:
                    other_candidates.append((dist, d))

            idle_candidates.sort(key=lambda t: t[0])
            other_candidates.sort(key=lambda t: t[0])

            take_idle = min(need, len(idle_candidates))
            for i in range(take_idle):
                reinforcements.add(idle_candidates[i][1])

            remaining = need - take_idle
            if remaining > 0:
                for i in range(min(remaining, len(other_candidates))):
                    reinforcements.add(other_candidates[i][1])

        # Precompute field limits
        field_limits = {f.id: getattr(f, "drones_for_full_protection", 0) for f in threat_fields}

        # Current counts of protecting drones per field (base state)
        counts = {}
        for f in threat_fields:
            counts[f.id] = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)

        # Add reinforcements to top field count
        if top_id in counts:
            counts[top_id] += len([d for d in reinforcements])
        else:
            counts[top_id] = len([d for d in reinforcements])

        # Apply reinforcement assignments
        for d in components:
            if d in reinforcements:
                grp = f"protecting {top_id}"
                safe = self._safe_group(grp, valid_groups)
                if safe:
                    environment.assign_group(d, safe)
                else:
                    environment.assign_group(d, "idle")
                continue

        # Map the rest, while preventing over-protection
        for d in components:
            if d in reinforcements:
                continue

            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)

            if st == "protecting" and tid is not None:
                limit = field_limits.get(tid, 0)
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
                limit = field_limits.get(tid, 0)
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
                # No active target or idle
                if "idle" in valid_groups:
                    environment.assign_group(d, "idle")
                else:
                    top_grp = f"protecting {top_id}"
                    safe = self._safe_group(top_grp, valid_groups)
                    if safe:
                        environment.assign_group(d, safe)
                    else:
                        environment.assign_group(d, "idle")