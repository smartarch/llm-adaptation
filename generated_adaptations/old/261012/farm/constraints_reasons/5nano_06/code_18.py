from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map each drone object to the group it's assigned to
        self._memory_assigned = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._memory_assigned[d] = "idle"
            return

        # Sort fields by threat level (descending)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)
        primary_field = fields_sorted[0]
        primary_group = f"protecting {primary_field.id}"

        N = len(components)
        half = N // 2

        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist_to_field(drone, field):
            cx, cy = field_center(field)
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return (dx * dx + dy * dy) ** 0.5

        new_assignments = {}

        # Stage A: Primary protection - closest drones
        n_needed = getattr(primary_field, "drones_for_full_protection", 0) or 0
        if n_needed > 0 and len(components) > 0:
            distances = [(dist_to_field(d, primary_field), d) for d in components]
            distances.sort(key=lambda t: t[0])
            take = min(n_needed, len(distances))
            for i in range(take):
                _, d = distances[i]
                new_assignments[d] = primary_group

        # Stage A2: Reinforce to guarantee primary_field reaches n_needed
        if n_needed > 0:
            current_primary = [d for d in components if new_assignments.get(d) == primary_group]
            if len(current_primary) < n_needed:
                candidates = [(dist_to_field(d, primary_field), d) for d in components]
                candidates.sort(key=lambda t: t[0])
                for dist, d in candidates:
                    if d in current_primary:
                        continue
                    new_assignments[d] = primary_group
                    current_primary.append(d)
                    if len(current_primary) >= n_needed:
                        break

        # Compute counts per field to know protection status
        def field_of_drone(grp):
            if grp is None or grp == "idle":
                return None
            if grp.startswith("protecting "):
                return grp[len("protecting "):]
            return None

        field_counts = {f.id: 0 for f in fields_sorted}
        protected_now = 0
        for d in components:
            g = new_assignments.get(d, "idle")
            if g != "idle":
                protected_now += 1
                fid = field_of_drone(g)
                if fid:
                    field_counts[fid] = field_counts.get(fid, 0) + 1

        primary_assigned = field_counts.get(primary_field.id, 0)
        primary_fully_protected = (primary_assigned >= n_needed) if n_needed > 0 else True

        # Stage B: After primary full, greedy marginal gain allocation to reach at least half
        if primary_field and primary_fully_protected:
            if protected_now < half:
                remaining_slots = half - protected_now
                # Build list of non-primary fields with remaining capacity
                non_primary = [f for f in fields_sorted if f.id != primary_field.id]
                # Sort by threat level desc, tie by threat level
                non_primary.sort(key=lambda f: f.threat_level, reverse=True)
                for field in non_primary:
                    grp = f"protecting {field.id}"
                    max_for_field = getattr(field, "drones_for_full_protection", 0) or 0
                    current_in_field = field_counts.get(field.id, 0)
                    if max_for_field <= 0 or current_in_field >= max_for_field:
                        continue

                    can_take = min(max_for_field - current_in_field, remaining_slots)
                    if can_take <= 0:
                        continue

                    # Try to allocate idle drones first
                    candidates = []
                    for d in components:
                        if new_assignments.get(d) == grp:
                            continue
                        dist = dist_to_field(d, field)
                        candidates.append((dist, d))
                    candidates.sort(key=lambda t: t[0])

                    for i in range(min(can_take, len(candidates))):
                        _, d = candidates[i]
                        new_assignments[d] = grp
                        field_counts[field.id] = field_counts.get(field.id, 0) + 1
                        protected_now += 1
                        remaining_slots -= 1
                        if remaining_slots == 0:
                            break
                    if remaining_slots == 0:
                        break

        # Stage C: Use idle drones to reinforce other fields up to their full protection quotas
        # After Stage B, there may be idle drones. Allocate them to fields with remaining capacity.
        idle_drones = [d for d in components if new_assignments.get(d) == "idle"]
        if idle_drones:
            # Build a prioritized list of fields with remaining capacity
            remaining_fields = []
            for f in fields_sorted:
                cap = getattr(f, "drones_for_full_protection", 0) or 0
                current = field_counts.get(f.id, 0)
                if cap > current:
                    remaining_fields.append((f.threat_level, f, cap - current))
            remaining_fields.sort(key=lambda t: (-t[0], -t[1].threat_level))

            # For each idle drone, assign to the best field with remaining capacity
            for d in list(idle_drones):
                if not remaining_fields:
                    break
                # pick the field with the highest threat level (and some proximity bias)
                best_threat, best_field, remaining = remaining_fields[0]
                grp = f"protecting {best_field.id}"
                new_assignments[d] = grp

                # update counts
                field_counts[best_field.id] = field_counts.get(best_field.id, 0) + 1
                remaining -= 1
                remaining_fields[0] = (best_threat, best_field, remaining)
                if remaining <= 0:
                    remaining_fields.pop(0)
                idle_drones.remove(d)

        # Stage D: Any remaining drones become idle
        for d in components:
            if d not in new_assignments:
                new_assignments[d] = "idle"

        # Stage E: Apply assignments and update memory
        for d, grp in new_assignments.items():
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self._memory_assigned[d] = grp