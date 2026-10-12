from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        n = len(components)

        # 2) Precompute field centers
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # 3) Sort fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        plan = {}        # drone_index -> group_name
        allocated = set()  # indices already allocated to a plan

        # Phase A: preserve existing protectors explicitly
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            for i, c in enumerate(components):
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                    plan[i] = group
                    allocated.add(i)

        # Phase B: full protection optimization using knapsack over remaining drones
        items = []       # fields considered for full protection
        weights = []     # needed drones for each field (beyond current protectors in plan)
        values = []      # threat_level for each field
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            cap = int(getattr(f, "drones_for_full_protection", 0))

            # current protectors already planned for this field
            current_in_plan = sum(1 for i, g in plan.items() if g == group)
            needed = max(0, cap - current_in_plan)
            if needed > 0:
                items.append(f)
                weights.append(needed)
                values.append(float(getattr(f, "threat_level", 0)))

        available = n - len(allocated)
        chosen_indices = []
        if items and available > 0:
            # 0-1 Knapsack: maximize sum(threat_level) with total cost <= available
            m = len(weights)
            # dp[w] = best total threat value achievable with total cost w
            NEG = -1e9
            dp = [NEG] * (available + 1)
            dp[0] = 0.0
            # take[i][w] = whether item i was taken to reach capacity w
            take = [[False] * (available + 1) for _ in range(m)]

            for i in range(m):
                w = weights[i]
                val = values[i]
                for cap in range(available, w - 1, -1):
                    if dp[cap - w] > NEG/2 and dp[cap - w] + val > dp[cap]:
                        dp[cap] = dp[cap - w] + val
                        take[i][cap] = True

            # find best weight
            best_w = max(range(available + 1), key=lambda ww: dp[ww])
            # reconstruct chosen items
            for i in range(m - 1, -1, -1):
                if take[i][best_w]:
                    chosen_indices.append(i)
                    best_w -= weights[i]

            # map to actual fields
            chosen_fields = [items[i] for i in chosen_indices]

            # allocate full protection for chosen fields
            for f in chosen_fields:
                group = f"protecting {f.id}"
                cx, cy = centers[f.id]
                cap = int(getattr(f, "drones_for_full_protection", 0)
                          )
                current_in_plan = sum(1 for i, g in plan.items() if g == group)
                needed = max(0, cap - current_in_plan)
                if needed <= 0:
                    continue

                candidates = [i for i in range(n) if i not in allocated]
                if not candidates:
                    break

                dist_list = []
                for idx in candidates:
                    loc = getattr(components[idx], "location", None)
                    if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                        d2 = float("inf")
                    else:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        d2 = dx*dx + dy*dy
                    dist_list.append((d2, idx))
                dist_list.sort(key=lambda t: t[0])

                for _, idx in dist_list[:needed]:
                    plan[idx] = group
                    allocated.add(idx)

        # Phase C: Partial distribution (allocate remaining drones to still-threatened fields)
        remaining = [i for i in range(n) if i not in allocated]

        for f in threat_fields_sorted:
            if not remaining:
                break
            group = f"protecting {f.id}"
            cx, cy = centers[f.id]
            cap = int(getattr(f, "drones_for_full_protection", 0))

            current_count = sum(1 for i in range(n) if plan.get(i) == group)
            needed_partial = max(0, cap - current_count)
            if needed_partial <= 0:
                continue

            for _ in range(needed_partial):
                if not remaining:
                    break
                best_idx = None
                best_dist = float("inf")
                for idx in list(remaining):
                    loc = getattr(components[idx], "location", None)
                    if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                        continue
                    d = (loc.x - cx)**2 + (loc.y - cy)**2
                    if d < best_dist:
                        best_dist = d
                        best_idx = idx
                if best_idx is None:
                    break
                plan[best_idx] = group
                allocated.add(best_idx)
                remaining.remove(best_idx)

        # Final assignment: every drone must be in a group
        for i, drone in enumerate(components):
            environment.assign_group(drone, plan.get(i, "idle"))