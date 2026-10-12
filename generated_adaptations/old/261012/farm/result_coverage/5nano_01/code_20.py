from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        n = len(components)
        # 1) Collect fields with positive threat
        threat_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Build current protectors by field
        protectors_by_field = {}
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    protectors_by_field.setdefault(tid, []).append(idx)

        # 3) Compute remaining need for each field to reach full protection
        remaining_need = {}
        preselected = set()  # fields already fully protected (remaining_need == 0)
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current = len(protectors_by_field.get(f.id, []))
            rem = max(0, needed - current)
            remaining_need[f.id] = rem
            if rem == 0:
                preselected.add(f.id)

        # 4) Idle drones (not currently protecting anything)
        idle_indices = [i for i, d in enumerate(components) if getattr(d, "state", "") != "protecting"]

        # 5) 0/1 Knapsack to select which fields to fully protect
        # Items: fields with rem > 0
        items = []
        for f in threat_fields:
            rem = remaining_need.get(f.id, 0)
            if rem > 0:
                items.append((f, rem, f.threat_level))

        # Capacity is the number of idle drones available for Phase 1
        capacity = len(idle_indices)

        # DP arrays
        # dp[c] = max threat-level achieved with total extra drones c
        dp = [-1.0] * (capacity + 1)
        dp[0] = 0.0
        # To reconstruct, store (item_index, prev_capacity)
        take = [(-1, -1)] * (capacity + 1)

        # Map items to indices
        m = len(items)
        for it_idx, (f, rem, val) in enumerate(items):
            w = rem  # cost in extra drones
            for c in range(capacity, w - 1, -1):
                if dp[c - w] >= 0 and dp[c - w] + val > dp[c]:
                    dp[c] = dp[c - w] + val
                    take[c] = (it_idx, c - w)

        # Find best capacity
        best_c = max(range(capacity + 1), key=lambda c: dp[c] if dp[c] >= 0 else -1e9)
        chosen_items = []
        c = best_c
        while c > 0:
            it_idx, prev_c = take[c]
            if it_idx == -1:
                break
            chosen_items.append(it_idx)
            c = prev_c

        # Build set of fully protected field IDs
        selected_field_ids = set(preselected)
        chosen_fields = []
        for it_idx in chosen_items:
            f, rem, _ = items[it_idx]
            if f.id not in selected_field_ids:
                selected_field_ids.add(f.id)
                chosen_fields.append(f)

        # 6) Phase 1 allocation: allocate to selected fields
        assigned = {}       # drone_index -> group_id
        allocated = set()     # drones already allocated to protecting group

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Ensure we sort by threat level for stable prioritization
        for f in sorted(chosen_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            rem = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(protectors_by_field.get(f.id, [])))
            if rem <= 0:
                # already fully protected; mark existing protectors
                for idx in protectors_by_field.get(f.id, []):
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)
                continue

            cx, cy = center_of(f)
            current_ids = [idx for idx in protectors_by_field.get(f.id, []) if idx not in allocated]
            # Keep closest current protectors
            def dist_to_center_by_field(idx, field=f):
                d = components[idx]
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - ((field.left + field.right) / 2.0)
                dy = loc.y - ((field.top + field.bottom) / 2.0)
                return (dx*dx + dy*dy) ** 0.5

            current_sorted = sorted(current_ids, key=lambda i: dist_to_center_by_field(i))
            keep = current_sorted[:min(len(current_sorted), rem)]
            for idx in keep:
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)

            remaining = rem - len(keep)
            if remaining > 0:
                # Fill with closest idle drones
                candidates = []
                for idx in idle_indices:
                    if idx in allocated:
                        continue
                    d = components[idx]
                    loc = getattr(d, "location", None)
                    dist = float("inf")
                    if loc is not None:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    candidates.append((dist, idx))
                candidates.sort()
                for i in range(min(remaining, len(candidates))):
                    idx = candidates[i][1]
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)

        # 7) Phase 2: Partial protection with remaining idle drones
        # Recompute remaining needs after Phase 1
        remaining_to_protect = {}
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current_count = len([idx for idx, gid in assigned.items() if gid == f"protecting {f.id}"])
            existing = len(protectors_by_field.get(f.id, []))
            remaining_to_protect[f.id] = max(0, needed - (current_count + existing if f.id in selected_field_ids else current_count))

        # Build the list of genuinely idle drones (not allocated)
        idle_remaining = [i for i in idle_indices if i not in allocated]

        # Fields needing partial protection (not fully protected yet)
        partial_fields = [f for f in threat_fields if remaining_to_protect.get(f.id, 0) > 0]
        partial_fields.sort(key=lambda ff: getattr(ff, "threat_level", 0), reverse=True)

        # Simple incremental partial: give at least one drone to top fields, then add more if drones remain
        partial_need = {f.id: max(1, remaining_to_protect.get(f.id, 0)) for f in partial_fields}
        # First pass: ensure at least 1 drone per top field
        for f in partial_fields:
            if not idle_remaining:
                break
            if partial_need.get(f.id, 0) <= 0:
                continue
            cx, cy = center_of(f)
            # pick nearest idle drone
            best_drone = None
            best_dist = float("inf")
            best_idx = None
            for idx in idle_remaining:
                d = components[idx]
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_drone = d
                    best_idx = idx
            if best_idx is not None:
                assigned[best_idx] = f"protecting {f.id}"
                allocated.add(best_idx)
                idle_remaining.remove(best_idx)
                partial_need[f.id] -= 1

        # Second pass: allocate remaining idle drones to the most-threat fields
        # Distribute evenly by threat level
        while idle_remaining and partial_fields:
            # pick field with highest threat
            f = partial_fields[0]
            cx, cy = center_of(f)
            best_idx = None
            best_dist = float("inf")
            for idx in idle_remaining:
                d = components[idx]
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
            if best_idx is None:
                break
            assigned[best_idx] = f"protecting {f.id}"
            allocated.add(best_idx)
            idle_remaining.remove(best_idx)

        # 8) Final: apply groups
        for idx, d in enumerate(components):
            if idx in assigned:
                environment.assign_group(d, assigned[idx])
            else:
                environment.assign_group(d, "idle")