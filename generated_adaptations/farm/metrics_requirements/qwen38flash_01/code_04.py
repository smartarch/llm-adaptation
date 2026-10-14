import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        num_drones = len(components)
        if num_drones == 0:
            return

        active_fields = [f for f in environment.fields if f.threat_level > 0]
        if not active_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Sort by threat descending (most threatened first)
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)
        most_threatened_id = active_fields[0].id

        # --- Helper functions ---
        def field_center(field):
            fx = (getattr(field, 'left', 0) + getattr(field, 'right', 0)) / 2.0
            fy = (getattr(field, 'top', 0) + getattr(field, 'bottom', 0)) / 2.0
            return fx, fy

        def dist(drone, field):
            fx, fy = field_center(field)
            dx = getattr(drone, 'x', 0) - fx
            dy = getattr(drone, 'y', 0) - fy
            return math.sqrt(dx * dx + dy * dy)

        def current_field(drone):
            return getattr(drone, 'target_id', None)

        # --- Step 1: Knapsack-based selection of fields to fully protect ---
        # Use DP knapsack if small enough, otherwise greedy by ratio
        n = len(active_fields)
        W = num_drones  # total drone budget

        # Enforce most-threatened field is included
        cost_must = active_fields[0].drones_for_full_protection
        remaining_budget = W - cost_must
        remaining_fields = active_fields[1:]

        if remaining_budget < 0:
            # Can't even fully protect the most threatened - just assign all to it
            selected_fields = [active_fields[0]]
        elif remaining_fields and remaining_budget > 0:
            # DP knapsack on remaining fields
            m = len(remaining_fields)
            # dp[w] = (max_threat, selected_indices)
            dp = [[0] * (remaining_budget + 1) for _ in range(m + 1)]
            for i in range(1, m + 1):
                cost_i = remaining_fields[i - 1].drones_for_full_protection
                val_i = remaining_fields[i - 1].threat_level
                for w in range(remaining_budget + 1):
                    dp[i][w] = dp[i - 1][w]
                    if w >= cost_i:
                        candidate = dp[i - 1][w - cost_i] + val_i
                        if candidate > dp[i][w]:
                            dp[i][w] = candidate
            # Backtrack to find selected fields
            sel_indices = []
            w = remaining_budget
            for i in range(m, 0, -1):
                cost_i = remaining_fields[i - 1].drones_for_full_protection
                val_i = remaining_fields[i - 1].threat_level
                if w >= cost_i and dp[i][w] == dp[i - 1][w - cost_i] + val_i:
                    sel_indices.append(i - 1)
                    w -= cost_i
            selected_fields = [active_fields[0]]
            for idx in sel_indices:
                selected_fields.append(remaining_fields[idx])
        else:
            selected_fields = [active_fields[0]]

        # Fields NOT selected go into a "secondary" list for partial coverage
        selected_ids = {f.id for f in selected_fields}
        secondary_fields = [f for f in active_fields if f.id not in selected_ids]
        secondary_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # --- Step 2: Assign drones to selected fields (full groups) ---
        assignments = {f.id: [] for f in active_fields}  # all fields can get partial
        assigned_set = set()

        # Sort selected fields by threat descending for assignment order
        selected_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for field in selected_fields:
            need = field.drones_for_full_protection
            available = [d for d in components if id(d) not in assigned_set]

            # Partition: already on this field vs not (stability preference)
            on_this = [d for d in available if current_field(d) == field.id]
            off_this = [d for d in available if current_field(d) != field.id]

            # Within each group, prefer closer drones
            on_this.sort(key=lambda d: dist(d, field))
            off_this.sort(key=lambda d: dist(d, field))

            # Take from on_this first (stability), then off_this (closest)
            chosen = []
            for d in on_this:
                if len(chosen) >= need:
                    break
                chosen.append(d)
            for d in off_this:
                if len(chosen) >= need:
                    break
                chosen.append(d)

            for d in chosen:
                assignments[field.id].append(d)
                assigned_set.add(id(d))

        # --- Step 3: Distribute remaining drones to secondary fields (partial) ---
        # Sort by threat, prioritize fields where a few extra drones complete protection
        # Also consider: can we COMPLETE a field with leftover drones?
        for field in secondary_fields:
            need = field.drones_for_full_protection
            available = [d for d in components if id(d) not in assigned_set]
            if not available:
                break
            # Only assign if we can reach full protection or field is high threat
            # Check if we have enough to complete
            if len(available) < need:
                # Don't do partial unless no selected field can use them
                # Actually, partial is better than idle per requirement
                pass

            remaining_cap = need - len(assignments[field.id])
            if remaining_cap <= 0:
                continue

            on_this = [d for d in available if current_field(d) == field.id]
            off_this = [d for d in available if current_field(d) != field.id]
            on_this.sort(key=lambda d: dist(d, field))
            off_this.sort(key=lambda d: dist(d, field))

            chosen = on_this[:remaining_cap]
            if len(chosen) < remaining_cap:
                chosen += off_this[:remaining_cap - len(chosen)]

            for d in chosen:
                assignments[field.id].append(d)
                assigned_set.add(id(d))

        # --- Step 4: Any remaining drones - add to selected fields if capacity allows,
        # otherwise secondary fields, otherwise idle ---
        still_idle = [d for d in components if id(d) not in assigned_set]
        if still_idle:
            # Try to boost selected fields (but don't overprotect)
            for field in selected_fields:
                if not still_idle:
                    break
                cap = field.drones_for_full_protection - len(assignments[field.id])
                if cap <= 0:
                    continue
                still_idle.sort(key=lambda d: dist(d, field))
                take = min(cap, len(still_idle))
                for d in still_idle[:take]:
                    assignments[field.id].append(d)
                    assigned_set.add(id(d))
                still_idle = still_idle[take:]

            # Then secondary fields
            for field in secondary_fields:
                if not still_idle:
                    break
                cap = field.drones_for_full_protection - len(assignments[field.id])
                if cap <= 0:
                    continue
                still_idle.sort(key=lambda d: dist(d, field))
                take = min(cap, len(still_idle))
                for d in still_idle[:take]:
                    assignments[field.id].append(d)
                    assigned_set.add(id(d))
                still_idle = still_idle[take:]

        # --- Step 5: Final stability check ---
        # If a drone was on field X last time and X is still selected/active,
        # and it got assigned elsewhere, consider keeping it on X (reduce thrashing)
        # (Already handled by "on_this first" logic above)

        # --- Step 6: Execute assignments ---
        for drone in components:
            did = id(drone)
            placed = False
            for fid, drones in assignments.items():
                if drone in drones:
                    environment.assign_group(drone, f"protecting {fid}")
                    placed = True
                    break
            if not placed:
                environment.assign_group(drone, "idle")