from generated_adaptations.base_classes.farm import FarmAdaptation
import abc

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of the field a drone protected in the previous step (None if idle)
        self.prev_assignments = {}

    def _center_of_field(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return (cx, cy)

    def _dist_to_field(self, drone, field):
        cx, cy = self._center_of_field(field)
        dx = getattr(drone.location, "x", 0.0) - cx
        dy = getattr(drone.location, "y", 0.0) - cy
        return (dx*dx + dy*dy) ** 0.5

    def _drones_protecting(self, drones, field):
        if field is None:
            return []
        return [
            d for d in drones
            if getattr(d, "state", None) in ("protecting", "moving_to_field")
            and getattr(d, "target_id", None) == field.id
        ]

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields
        fields = list(environment.fields)
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing threatened, idle all
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            self.prev_assignments = {}
            return

        # Sort threatened fields by threat level (desc). We keep a stable tie-break on drones_for_full_protection
        threatened.sort(
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "drones_for_full_protection", 0)),
            reverse=True
        )

        # Build a list of candidate fields that can be fully protected (cost > 0)
        items = []
        for f in threatened:
            cost = getattr(f, "drones_for_full_protection", 0)
            if cost <= 0:
                continue
            value = getattr(f, "threat_level", 0)
            items.append((f, cost, value))

        total_drones = len(components)
        # 0/1 Knapsack to maximize total threat protection
        # dp[c] = (max_value, chosen_items_bitmask)
        max_cap = total_drones
        n = len(items)
        dp = [(-1.0, 0) for _ in range(max_cap + 1)]
        dp[0] = (0.0, 0)
        # bitmask approach (n <= number of threatened fields with cost>0; typically small)
        for i, (f, cost, value) in enumerate(items):
            for c in range(max_cap, cost - 1, -1):
                if dp[c - cost][0] >= 0:
                    new_val = dp[c - cost][0] + value
                    if new_val > dp[c][0]:
                        dp[c] = (new_val, dp[c - cost][1] | (1 << i))

        # Find best total value and corresponding bitmask
        best_c = max(range(max_cap + 1), key=lambda c: dp[c][0])
        best_mask = dp[best_c][1]

        # Selected fields to fully protect
        chosen_fields = []
        for i, (f, cost, value) in enumerate(items):
            if (best_mask >> i) & 1:
                chosen_fields.append(f)

        # Map field_id -> group name
        field_to_group = {f.id: f"protecting {f.id}" for f in threatened}

        total_selected_cost = sum(getattr(f, "drones_for_full_protection", 0) for f in chosen_fields)

        assigned_to = {d: None for d in components}  # drone -> field_id or None

        # Helper to get current protectors per field
        current_by_field = {f.id: self._drones_protecting(components, f) for f in threatened}

        # Step 1: Allocate to chosen (fully protected) fields
        # Sort chosen fields by threat (desc) to allocate closest drones predictably
        chosen_fields.sort(key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "drones_for_full_protection", 0)), reverse=True)

        for f in chosen_fields:
            grp = field_to_group[f.id]
            desired = getattr(f, "drones_for_full_protection", 0)
            current = current_by_field.get(f.id, [])
            # First, keep existing protectors on this field (to reduce churn)
            kept = []
            for d in current:
                if assigned_to[d] is None and len(kept) < max(0, desired):
                    environment.assign_group(d, grp)
                    assigned_to[d] = f.id
                    kept.append(d)
            current = kept

            # If we still need more to reach desired, assign closest available drones
            if len(current) < desired:
                needed = desired - len(current)
                candidates = []
                for d in components:
                    if assigned_to[d] is not None:
                        continue
                    dist = self._dist_to_field(d, f)
                    bias = -1e-6 if self.prev_assignments.get(d) == f.id else 0.0
                    candidates.append((dist + bias, d))
                candidates.sort(key=lambda x: x[0])
                for _, d in candidates[:needed]:
                    environment.assign_group(d, grp)
                    assigned_to[d] = f.id
                    current.append(d)

        # Step 2: Allocate remaining drones to other threatened fields to raise protection level
        remaining_drones = [d for d in components if assigned_to[d] is None]
        for f in threatened:
            if f in chosen_fields:
                continue
            grp = field_to_group[f.id]
            desired = getattr(f, "drones_for_full_protection", 0)
            current = self._drones_protecting(components, f)
            if len(current) > desired:
                # Drop farthest protectors to fit the limit
                current_sorted = sorted(current, key=lambda d: self._dist_to_field(d, f), reverse=True)
                to_drop = current_sorted[desired:]
                for d in to_drop:
                    environment.assign_group(d, "idle")
                    assigned_to[d] = None
                current = current_sorted[:desired]

            if len(current) < desired:
                needed = desired - len(current)
                pool = [d for d in remaining_drones if d not in current]
                candidates = []
                for d in pool:
                    dist = self._dist_to_field(d, f)
                    bias = 0.0
                    if self.prev_assignments.get(d) == f.id:
                        bias = -1e-6
                    candidates.append((dist + bias, d))
                candidates.sort(key=lambda x: x[0])
                for _, d in candidates[:needed]:
                    environment.assign_group(d, grp)
                    assigned_to[d] = f.id
                    remaining_drones.remove(d)

        # Step 3: Balance to meet at least half protection rule
        protecting_now = [d for d in components if assigned_to[d] is not None]
        if len(protecting_now) < total_drones * 0.5:
            idle_drones = [d for d in components if assigned_to[d] is None]
            # capacities per field remaining (how many more needed to reach full protection)
            capacities = {}
            for f in threatened:
                current = [d for d in components if assigned_to[d] == f.id]
                cap = max(0, getattr(f, "drones_for_full_protection", 0) - len(current))
                capacities[f.id] = cap

            for d in idle_drones:
                if len(protecting_now) >= total_drones * 0.5:
                    break
                best_field = None
                best_dist = float("inf")
                for f in threatened:
                    if capacities.get(f.id, 0) <= 0:
                        continue
                    dist = self._dist_to_field(d, f)
                    if dist < best_dist or (dist == best_dist and self.prev_assignments.get(d) == f.id):
                        best_dist = dist
                        best_field = f
                if best_field is not None:
                    env_group = field_to_group[best_field.id]
                    environment.assign_group(d, env_group)
                    assigned_to[d] = best_field.id
                    capacities[best_field.id] -= 1
                    protecting_now.append(d)

        # Step 4: Idle remaining
        for d in components:
            if assigned_to.get(d) is None:
                environment.assign_group(d, "idle")

        # Memory update for next step
        new_memory = {}
        for d in components:
            new_memory[d] = assigned_to.get(d)  # field_id or None
        self.prev_assignments = new_memory