from generated_adaptations.base_classes.farm import FarmAdaptation

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
        # Collect threatened fields
        fields = list(environment.fields)
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing threatened, idle all
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            self.prev_assignments = {}
            return

        # Sort threatened fields by threat level (desc)
        threatened.sort(
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "drones_for_full_protection", 0)),
            reverse=True
        )

        # Map field_id -> group name
        field_to_group = {f.id: f"protecting {f.id}" for f in threatened}

        total_drones = len(components)
        assigned_to = {d: None for d in components}  # drone -> field_id or None

        # Current protectors per field
        current_by_field = {f.id: self._drones_protecting(components, f) for f in threatened}

        # Step 1: Top field protection
        top_field = threatened[0]
        top_group = field_to_group[top_field.id]
        top_desired = getattr(top_field, "drones_for_full_protection", 0)
        top_desired = min(top_desired, total_drones)

        top_current = current_by_field[top_field.id]

        selected_top = []
        # Preserve existing protectors on top field to reduce churn
        for d in top_current:
            if assigned_to[d] is None and len(selected_top) < top_desired:
                environment.assign_group(d, top_group)
                assigned_to[d] = top_field.id
                selected_top.append(d)

        # If more needed, pick closest available drones
        if len(selected_top) < top_desired:
            needed = top_desired - len(selected_top)
            candidates = []
            for d in components:
                if assigned_to[d] is not None:
                    continue
                dist = self._dist_to_field(d, top_field)
                bias = -1e-6 if self.prev_assignments.get(d) == top_field.id else 0.0
                candidates.append((dist + bias, d))
            candidates.sort(key=lambda x: x[0])
            for _, d in candidates[:needed]:
                environment.assign_group(d, top_group)
                assigned_to[d] = top_field.id
                selected_top.append(d)

        # If still not enough (scarce drones), assign remaining to top (partial protection)
        if len(selected_top) < max(1, top_desired):
            remaining = [d for d in components if assigned_to[d] is None]
            for d in remaining:
                environment.assign_group(d, top_group)
                assigned_to[d] = top_field.id
                selected_top.append(d)
                if len(selected_top) >= max(1, top_desired):
                    break

        # Step 2: Other threatened fields
        remaining_drones = [d for d in components if assigned_to[d] is None]
        for field in threatened[1:]:
            grp = field_to_group[field.id]
            desired = getattr(field, "drones_for_full_protection", 0)

            current = self._drones_protecting(components, field)
            if len(current) > desired:
                # Drop farthest protectors to fit
                current_sorted = sorted(current, key=lambda d: self._dist_to_field(d, field), reverse=True)
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
                    dist = self._dist_to_field(d, field)
                    bias = 0.0
                    if self.prev_assignments.get(d) == field.id:
                        bias = -1e-6  # prefer continuing to protect this field
                    candidates.append((dist + bias, d))
                candidates.sort(key=lambda x: x[0])

                for _, d in candidates[:needed]:
                    environment.assign_group(d, grp)
                    assigned_to[d] = field.id
                    remaining_drones.remove(d)

        # Step 3: Ensure at least half drones are protecting (if possible)
        protecting_now = [d for d in components if assigned_to[d] is not None]
        if len(protecting_now) < total_drones * 0.5:
            idle_drones = [d for d in components if assigned_to[d] is None]
            # capacities per field (how many more drones can be assigned to reach full protection)
            capacities = {}
            for f in threatened:
                current = [d for d in components if assigned_to[d] == f.id]
                cap = max(0, getattr(f, "drones_for_full_protection", 0) - len(current))
                capacities[f.id] = cap

            for d in idle_drones:
                if len(protecting_now) >= total_drones * 0.5:
                    break
                # choose best field with capacity, nearest
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