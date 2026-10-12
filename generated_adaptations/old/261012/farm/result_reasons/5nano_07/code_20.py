from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # memory: maps drone id to last field id it protected (or None if idle)
        self._drone_last_field = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist_to_field(self, drone, field):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        cx, cy = self._field_center(field)
        dx = loc.x - cx
        dy = loc.y - cy
        return (dx*dx + dy*dy) ** 0.5

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, set all drones to idle
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None
            return

        # Sort fields by threat level (most threatened first)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)
        field_by_id = {f.id: f for f in fields}
        costs = {f.id: int(getattr(f, "drones_for_full_protection", 0)) for f in fields}

        # Build current protect map: field_id -> list of drones protecting it
        current_protect = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protect.setdefault(t, []).append(d)

        assigned = set()

        # Phase 1: Top field
        top = fields_sorted[0]
        top_group = f"protecting {top.id}"
        req_top = costs[top.id]
        cur_top = len(current_protect.get(top.id, []))

        if cur_top < req_top:
            need = req_top - cur_top

            # Pool of movable drones: idle or surplus from other fields
            pool = []
            for cand in components:
                # Skip drones already protecting the top field
                if getattr(cand, "state", None) == "protecting" and getattr(cand, "target_id", None) == top.id:
                    continue

                movable = False
                if getattr(cand, "state", None) != "protecting":
                    movable = True
                else:
                    other_id = getattr(cand, "target_id", None)
                    other_field = field_by_id.get(other_id)
                    if other_field is not None:
                        other_cur = len(current_protect.get(other_id, []))
                        other_req = costs.get(other_id, 0)
                        if other_cur > other_req:
                            movable = True
                    else:
                        movable = True  # unknown field, treat as movable

                if movable:
                    dist = self._dist_to_field(cand, top)
                    last_match = (self._drone_last_field.get(id(cand)) == top.id)
                    pool.append((dist, 0 if last_match else 1, cand))
            pool.sort()

            picked = 0
            for dist, _, cand in pool:
                if picked >= need:
                    break
                if top_group not in group_ids:
                    break
                environment.assign_group(cand, top_group)
                self._drone_last_field[id(cand)] = top.id
                assigned.add(cand)
                # Update current_protect to reflect this move
                old_id = getattr(cand, "target_id", None)
                if getattr(cand, "state", None) == "protecting" and old_id is not None:
                    if cand in current_protect.get(old_id, []):
                        current_protect[old_id].remove(cand)
                current_protect.setdefault(top.id, []).append(cand)
                picked += 1

        # Phase 2: Remaining fields (knapsack-guided)
        # Updated current protection after Phase 1
        updated_current = {fid: list(lst) for fid, lst in current_protect.items()}
        if top.id not in updated_current:
            updated_current[top.id] = []
        for d in assigned:
            if d not in updated_current[top.id]:
                updated_current[top.id].append(d)

        # Build pool2: movable drones not assigned in Phase 1
        pool2 = []
        for d in components:
            if d in assigned:
                continue
            # Do not pull from the top field
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id:
                continue

            movable = False
            if getattr(d, "state", None) != "protecting":
                movable = True
            else:
                other_id = getattr(d, "target_id", None)
                other_field = field_by_id.get(other_id)
                if other_field is not None:
                    other_cur = len(updated_current.get(other_id, []))
                    other_req = costs.get(other_id, 0)
                    if other_cur > other_req:
                        movable = True
                else:
                    movable = True
            if movable:
                pool2.append(d)

        # Build remaining fields to protect (excluding top)
        remaining_fields = []
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            req = costs.get(f.id, 0)
            if req <= 0:
                continue
            current = len(updated_current.get(f.id, []))
            if current < req:
                remaining_fields.append((f, current, req))

        # 0/1 knapsack: maximize threat_level with cost = drones_for_full_protection
        # Only consider fields not yet fully protected
        # Budget is the number of movable drones in pool2
        budget = len(pool2)

        # Build items for DP
        items = []
        for f, current, req in remaining_fields:
            cost = int(req - current)
            if cost <= 0:
                continue
            value = getattr(f, "threat_level", 0)
            items.append((f, cost, value))

        # DP: dp[w] = max value, keep track of choice
        dp = [-1] * (budget + 1)
        take = [None] * (budget + 1)
        dp[0] = 0

        for idx, (f, cost, value) in enumerate(items):
            for w in range(budget, cost - 1, -1):
                if dp[w - cost] != -1:
                    new_val = dp[w - cost] + value
                    if new_val > dp[w]:
                        dp[w] = new_val
                        take[w] = (idx, w - cost)

        # Find best value within budget
        best_w = max(range(budget + 1), key=lambda w: dp[w] if dp[w] >= 0 else -1)
        best_val = dp[best_w]
        chosen_indices = set()
        w = best_w
        while w is not None and take[w] is not None:
            idx, prev_w = take[w]
            chosen_indices.add(idx)
            w = prev_w

        chosen_fields = [items[i][0] for i in chosen_indices]

        # Phase 2 allocation: allocate drones to chosen fields by distance, greedily per field
        # Rebuild a pool used for Phase 2 (pool2), and a mutable set of available drones
        available = list(pool2)
        # Sort chosen fields by threat density to reduce risk of high-threat fields being underprotected
        chosen_fields.sort(key=lambda ff: getattr(ff, "threat_level", 0) / max(1, int(costs.get(ff.id, 1))), reverse=True)

        for f in chosen_fields:
            req = costs.get(f.id, 0)
            current = len(updated_current.get(f.id, []))
            need = int(req - current)
            if need <= 0:
                continue

            # Pick the closest available drones
            scored = []
            for cand in available:
                if cand in assigned:
                    continue
                dist = self._dist_to_field(cand, f)
                last_match = (self._drone_last_field.get(id(cand)) == f.id)
                scored.append((dist, 0 if last_match else 1, cand))
            scored.sort()

            picked = 0
            target_group = f"protecting {f.id}"
            for dist, _, cand in scored:
                if picked >= need:
                    break
                if target_group not in group_ids:
                    continue
                environment.assign_group(cand, target_group)
                self._drone_last_field[id(cand)] = f.id
                assigned.add(cand)
                # Update updated_current
                updated_current.setdefault(f.id, []).append(cand)
                # Remove from available
                if cand in available:
                    available.remove(cand)
                picked += 1

        # Final: idle everything not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None