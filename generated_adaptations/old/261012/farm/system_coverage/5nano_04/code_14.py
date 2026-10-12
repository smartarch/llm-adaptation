from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Build maps
        field_map = {f.id: f for f in fields}
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}

        # Current defenders per field
        current_defenders = {f.id: 0 for f in fields}
        current_defenders_set = {f.id: set() for f in fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_defenders:
                    current_defenders[tid] += 1
                    current_defenders_set[tid].add(c)

        D = len(components)

        # Identify top field (max threat)
        top_field = max(fields, key=lambda f: f.threat_level)
        top_id = top_field.id
        top_required = getattr(top_field, "drones_for_full_protection", 0)
        top_current = current_defenders.get(top_id, 0)
        top_need = max(0, top_required - top_current)

        final_group = {}  # drone -> group_id
        allocated = set()  # drones already assigned in this step

        def assign_to_group(drone, gid):
            final_group[drone] = gid
            allocated.add(drone)

        # Phase 1: fully protect the top field with closest drones
        if top_need > 0:
            cx, cy = centers[top_id]
            candidates = []
            for c in components:
                if c in allocated:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_id:
                    continue
                loc = getattr(c, "location", None)
                dist2 = float('inf')
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, c))
            candidates.sort(key=lambda t: t[0])
            for i in range(min(top_need, len(candidates))):
                d = candidates[i][1]
                assign_to_group(d, f"protecting {top_id}")

        # Recompute top defenders after phase 1
        top_defenders_after = current_defenders.get(top_id, 0)
        for d, gid in final_group.items():
            if gid == f"protecting {top_id}":
                top_defenders_after += 1

        # Phase 2: 0/1 knapsack to decide which other fields to fully protect
        # Build candidate fields (excluding top)
        items = []
        field_ids_for_dp = []
        for f in fields:
            if f.id == top_id:
                continue
            current = current_defenders.get(f.id, 0)
            cost = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            threat = getattr(f, "threat_level", 0.0)
            if cost == 0:
                # Already fully protected; ensure its defenders are represented
                for dr in current_defenders_set.get(f.id, set()):
                    if dr not in allocated:
                        final_group[dr] = f"protecting {f.id}"
                        allocated.add(dr)
                continue
            if cost > 0:
                items.append((f.id, cost, int(threat * 1000)))
                field_ids_for_dp.append(f.id)

        # Capacity: number of drones available to allocate to other fields
        # We cannot move top-field defenders, so capacity = total drones - top_defenders_after
        capacity = max(0, D - top_defenders_after)

        # Filter items that can fit into capacity
        items = [it for it in items if it[1] <= capacity]
        n = len(items)

        selected_ids = []
        if capacity > 0 and n > 0:
            # 0/1 knapsack: maximize value (threat * 1000)
            dp = [[0] * (capacity + 1) for _ in range(n + 1)]
            take = [[False] * (capacity + 1) for _ in range(n + 1)]
            for i in range(1, n + 1):
                fid, w, val = items[i - 1]
                for c in range(capacity + 1):
                    if w <= c:
                        newv = dp[i - 1][c - w] + val
                        if newv > dp[i - 1][c]:
                            dp[i][c] = newv
                            take[i][c] = True
                        else:
                            dp[i][c] = dp[i - 1][c]
                    else:
                        dp[i][c] = dp[i - 1][c]
            # Reconstruct
            rem = capacity
            for i in range(n, 0, -1):
                if take[i][rem]:
                    fid = items[i - 1][0]
                    selected_ids.append(fid)
                    rem -= items[i - 1][1]

        # Phase 2a: allocate drones to selected fields (closest first)
        # Build a quick map for current defenders to avoid breaking others
        for fid in selected_ids:
            f = field_map[fid]
            current = current_defenders.get(fid, 0)
            need = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if need <= 0:
                continue
            cx, cy = centers[fid]
            # Build candidates: drones not already allocated to top and not currently protecting top
            candidates = []
            for c in components:
                if c in allocated:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_id:
                    continue
                loc = getattr(c, "location", None)
                dist2 = float('inf')
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, c))
            candidates.sort(key=lambda t: t[0])
            for i in range(min(need, len(candidates))):
                d = candidates[i][1]
                final_group[d] = f"protecting {fid}"
                allocated.add(d)

        # Phase 3: partial protection with remaining drones (one per field, ordered by threat)
        # Build list of fields not yet fully protected (excluding top if now full)
        not_full = []
        for f in fields:
            required = getattr(f, "drones_for_full_protection", 0)
            current = current_defenders.get(f.id, 0)
            # If top field is not top_id, ensure we respect its protection; otherwise skip
            if f.id == top_id:
                if required > 0 and current < required:
                    not_full.append((f.threat_level, f))
                continue
            if required > current:
                not_full.append((f.threat_level, f))
        not_full.sort(key=lambda t: t[0], reverse=True)

        # Build pool of unallocated drones
        unallocated = [c for c in components if c not in allocated and c not in final_group]
        for _, f in not_full:
            if not unallocated:
                break
            cx, cy = centers[f.id]
            # find closest unallocated drone
            best_idx = None
            best_dist = float('inf')
            for idx, drone in enumerate(unallocated):
                loc = getattr(drone, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                if dist2 < best_dist:
                    best_dist = dist2
                    best_idx = idx
            if best_idx is not None:
                drone = unallocated.pop(best_idx)
                final_group[drone] = f"protecting {f.id}"
                allocated.add(drone)

        # Phase 4: assign remaining drones to idle
        for c in components:
            if c in final_group:
                environment.assign_group(c, final_group[c])
            else:
                environment.assign_group(c, "idle")