from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persistent memory of last assigned group per drone (by id)
        self._last_assignment = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Helper: check if a drone is currently protecting a given field (by memory/state)
        def is_protecting_field(d, field_id):
            d_id = id(d)
            last_grp = self._last_assignment.get(d_id, None)
            if last_grp == f"protecting {field_id}":
                return True
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                return True
            return False

        # Helper: current protection count for a field
        def current_protect_count(field):
            count = 0
            for d in components:
                if is_protecting_field(d, field.id):
                    count += 1
            return count

        # Sort fields by threat level descending, then by id for determinism
        fields_sorted = sorted(
            fields,
            key=lambda f: (-getattr(f, "threat_level", 0), getattr(f, "id", "")),
        )

        # Prepare centers for distance calculations
        centers = {f.id: center_of(f) for f in fields_sorted}

        total_drones = len(components)
        step_assignment = {}

        if not fields_sorted:
            # No threats: all drones idle
            for d in components:
                step_assignment[id(d)] = "idle"
            for d in components:
                environment.assign_group(d, step_assignment[id(d)])
            self._last_assignment = step_assignment
            return

        # Step 1: Fully protect the top-threat field
        top = fields_sorted[0]
        current_top = current_protect_count(top)
        top_required = getattr(top, "drones_for_full_protection", 0)
        needed_top = max(0, top_required - current_top)

        # Preserve any drone already protecting the top (memory or state)
        for d in components:
            if is_protecting_field(d, top.id):
                step_assignment[id(d)] = f"protecting {top.id}"

        if needed_top > 0:
            center_top = centers[top.id]
            candidates = []
            for d in components:
                d_id = id(d)
                if d_id in step_assignment:
                    continue
                last = self._last_assignment.get(d_id, None)
                priority = 0 if (last == f"protecting {top.id}") or (
                    getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id
                ) else 1
                lx = getattr(d, "location").x
                ly = getattr(d, "location").y
                dist2 = (lx - center_top[0]) ** 2 + (ly - center_top[1]) ** 2
                candidates.append((priority, dist2, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            assigned = 0
            for _, _, d in candidates:
                if assigned >= needed_top:
                    break
                step_assignment[id(d)] = f"protecting {top.id}"
                assigned += 1

        # Step 2: After top is handled, select additional fields to fully protect via DP
        def protected_count(field):
            c = 0
            for d in components:
                if id(d) in step_assignment and step_assignment[id(d)] == f"protecting {field.id}":
                    c += 1
                elif is_protecting_field(d, field.id):
                    c += 1
            return c

        # Build candidate fields (excluding top) with their cost and threat
        candidates = []
        for f in fields_sorted[1:]:
            req = getattr(f, "drones_for_full_protection", 0)
            if req <= 0:
                continue
            current = protected_count(f)
            if current >= req:
                continue
            cost = req - current  # drones needed to fully protect this field
            threat = getattr(f, "threat_level", 0)
            candidates.append({"field": f, "cost": cost, "threat": threat})

        # Capacity for additional fields after top
        used_top_total = top_required if current_top < top_required else current_top
        capacity = max(0, total_drones - used_top_total)

        if candidates and capacity > 0:
            # DP knapsack to pick best subset of fields to maximize total threat
            # Only consider fields with cost <= capacity
            items = [it for it in candidates if it["cost"] <= capacity]
            if items:
                W = capacity
                dp = [-1.0] * (W + 1)
                dp[0] = 0.0
                prev = [-1] * (W + 1)
                take = [-1] * (W + 1)

                for idx, it in enumerate(items):
                    cost = it["cost"]
                    val = it["threat"]
                    for w in range(W, cost - 1, -1):
                        if dp[w - cost] >= 0 and dp[w - cost] + val > dp[w]:
                            dp[w] = dp[w - cost] + val
                            prev[w] = w - cost
                            take[w] = idx

                # Find best w
                best_w = max(range(W + 1), key=lambda w: dp[w] if dp[w] >= 0 else -1)
                if dp[best_w] > 0:
                    chosen_indices = []
                    w = best_w
                    while w > 0 and take[w] != -1:
                        idx = take[w]
                        chosen_indices.append(idx)
                        w = prev[w]
                    chosen_fields = [items[i]["field"] for i in chosen_indices]

                    # Allocate drones to chosen fields from the remaining pool
                    # Recompute unassigned fresh for allocation
                    unassigned = [d for d in components if id(d) not in step_assignment]

                    def pick_drones_for_field(field, needed, pool):
                        if needed <= 0:
                            return []
                        center = centers[field.id]
                        cand = []
                        for d in pool:
                            d_id = id(d)
                            last = self._last_assignment.get(d_id, None)
                            priority = 0 if (last == f"protecting {field.id}") or (
                                getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
                            ) else 1
                            dx = getattr(d, "location").x
                            dy = getattr(d, "location").y
                            dist2 = (dx - center[0]) ** 2 + (dy - center[1]) ** 2
                            cand.append((priority, dist2, d))
                        cand.sort(key=lambda t: (t[0], t[1]))
                        picks = []
                        for _, _, drone in cand:
                            if len(picks) >= needed:
                                break
                            picks.append(drone)
                        for dr in picks:
                            pool.remove(dr)
                        return picks

                    for f in chosen_fields:
                        current = protected_count(f)
                        needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
                        if needed <= 0:
                            continue
                        picked = pick_drones_for_field(f, needed, unassigned)
                        for d in picked:
                            step_assignment[id(d)] = f"protecting {f.id}"
        # Step 3: Idle remaining drones
        for d in components:
            if id(d) not in step_assignment:
                step_assignment[id(d)] = "idle"

        # Apply the assignments to the environment
        for d in components:
            environment.assign_group(d, step_assignment[id(d)])

        # Persist this step's assignments for the next step
        self._last_assignment = step_assignment