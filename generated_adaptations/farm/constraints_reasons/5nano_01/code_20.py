from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory to bias future allocations without breaking top-field guarantee
        self._prev_groups = {}
        # Simple stickiness metric: how long a drone has stayed with its current field
        self._stickiness = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threat-bearing fields
        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_field(drone, field):
            cx, cy = center(field)
            x = getattr(drone.location, "x", 0.0)
            y = getattr(drone.location, "y", 0.0)
            dx = x - cx
            dy = y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Map from field.id to its protect group
        field_group = {f.id: f"protecting {f.id}" for f in threat_fields}

        # If no threat, idle all
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._prev_groups[id(d)] = "idle"
                self._stickiness[id(d)] = 0
            return

        # Sort threat fields by threat level desc
        threat_sorted = sorted(threat_fields, key=lambda ff: ff.threat_level, reverse=True)
        most_field = threat_sorted[0]
        most_gid = field_group[most_field.id]
        most_cap = getattr(most_field, "drones_for_full_protection", 0)

        final_plan = {}

        # Step 1: Prefer keeping current top-field protectors
        current_top = [d for d in components if self._prev_groups.get(id(d)) == most_gid]
        chosen = []
        if len(current_top) >= most_cap:
            # If we already have enough protectors, pick the closest among them
            current_top_sorted = sorted(current_top, key=lambda d: dist_to_field(d, most_field))
            chosen = current_top_sorted[:most_cap]
        else:
            # Take all current protectors, then fill with closest others
            remaining_needed = most_cap - len(current_top)
            others = [d for d in components if d not in current_top]
            # Bias toward closer drones, then toward more sticky drones
            others.sort(key=lambda d: (dist_to_field(d, most_field), -self._stickiness.get(id(d), 0)))
            chosen = current_top + others[:remaining_needed]

        for d in chosen:
            final_plan[d] = most_gid
            self._prev_groups[id(d)] = most_gid

        # Step 2: Handle secondary threat fields
        remaining = [d for d in components if d not in chosen]
        for f in threat_sorted[1:]:
            gid = field_group[f.id]
            cap = getattr(f, "drones_for_full_protection", 0)

            current = [d for d in remaining if self._prev_groups.get(id(d)) == gid]
            cur = len(current)

            if cur > cap:
                # Over-protected: demote farthest drones
                dists = [(d, dist_to_field(d, f)) for d in current]
                dists.sort(key=lambda x: x[1], reverse=True)
                over = cur - cap
                for i in range(over):
                    d, _ = dists[i]
                    final_plan[d] = "idle"
                    self._prev_groups.pop(id(d), None)
                    self._stickiness.pop(id(d), None)
                current = [d for d in remaining if self._prev_groups.get(id(d)) == gid]
                cur = len(current)

            if cur < cap:
                need = cap - cur
                candidates = [d for d in remaining if self._prev_groups.get(id(d)) != gid]
                # Prefer nearest, then more sticky
                candidates.sort(key=lambda d: (dist_to_field(d, f), -self._stickiness.get(id(d), 0)))
                for i in range(min(need, len(candidates))):
                    d = candidates[i]
                    final_plan[d] = gid
                    self._prev_groups[id(d)] = gid

        # Step 3: Ensure at least half of drones are protecting
        total = len(components)
        protecting_now = [d for d in components if self._prev_groups.get(id(d)) in field_group.values()]
        if len(protecting_now) < (total / 2.0):
            needed = int((total / 2.0) - len(protecting_now))
            free = [d for d in components if self._prev_groups.get(id(d)) not in field_group.values()]
            for f in threat_sorted:
                if needed <= 0:
                    break
                gid = field_group[f.id]
                current_f = [d for d in components if self._prev_groups.get(id(d)) == gid]
                cap = getattr(f, "drones_for_full_protection", 0)
                if len(current_f) >= cap:
                    continue
                to_allocate = cap - len(current_f)
                free.sort(key=lambda d: (dist_to_field(d, f), -self._stickiness.get(id(d), 0)))
                take = min(to_allocate, len(free), needed)
                for i in range(take):
                    d = free[i]
                    final_plan[d] = gid
                    self._prev_groups[id(d)] = gid
                    # Increase stickiness for those who are newly assigned
                    self._stickiness[id(d)] = self._stickiness.get(id(d), 0) + 1
                needed -= take
                free = free[take:]

        # Finalize: assign valid groups only
        for d in components:
            if d in final_plan:
                gid = final_plan[d]
            else:
                prev = self._prev_groups.get(id(d))
                gid = prev if prev is not None else "idle"
            if gid not in group_ids:
                gid = "idle"
            final_plan[d] = gid

        # Apply assignments and update stickiness/memory
        for d, gid in final_plan.items():
            environment.assign_group(d, gid)

        # Update memory after applying plan
        for d in components:
            old_gid = self._prev_groups.get(id(d))
            new_gid = final_plan.get(d, old_gid)
            if old_gid == new_gid:
                self._stickiness[id(d)] = self._stickiness.get(id(d), 0) + 1
            else:
                self._stickiness[id(d)] = 1
            self._prev_groups[id(d)] = new_gid