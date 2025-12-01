from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map each drone object to the group it's assigned to
        self._memory_assigned = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Primary field to fully protect
        primary_field = fields_sorted[0] if fields_sorted else None
        primary_group = f"protecting {primary_field.id}" if primary_field else None

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

        # Stage A: Initially assign the closest n_needed drones to primary
        if primary_field:
            n_needed = getattr(primary_field, "drones_for_full_protection", 0) or 0
            if n_needed > 0 and len(components) > 0:
                distances = [(dist_to_field(d, primary_field), d) for d in components]
                distances.sort(key=lambda t: t[0])
                take = min(n_needed, len(distances))
                for i in range(take):
                    _, d = distances[i]
                    new_assignments[d] = primary_group

        # Stage A2: Guarantee primary_field has at least n_needed drones (fill if needed)
        if primary_field:
            n_needed = getattr(primary_field, "drones_for_full_protection", 0) or 0
            if n_needed > 0:
                current_primary = [d for d in components if new_assignments.get(d) == primary_group]
                if len(current_primary) < n_needed:
                    # Fill with closest drones not already on primary
                    candidates = [(dist_to_field(d, primary_field), d) for d in components]
                    candidates.sort(key=lambda t: t[0])
                    for dist, d in candidates:
                        if d in current_primary:
                            continue
                        new_assignments[d] = primary_group
                        current_primary.append(d)
                        if len(current_primary) >= n_needed:
                            break

        # Stage B: If primary is fully protected, ensure at least half are protecting something
        protected_now = sum(1 for d in components if new_assignments.get(d, None) is not None and new_assignments.get(d) != "idle")
        primary_assigned = 0
        if primary_field:
            primary_assigned = sum(1 for d in components if new_assignments.get(d) == primary_group)
        primary_fully_protected = (primary_field is None) or (primary_assigned >= getattr(primary_field, "drones_for_full_protection", 0) or getattr(primary_field, "drones_for_full_protection", 0) == 0)

        if primary_field and primary_fully_protected:
            if protected_now < half:
                remaining_slots = half - protected_now
                for field in fields_sorted[1:]:
                    grp = f"protecting {field.id}"
                    n_limit = getattr(field, "drones_for_full_protection", 0) or 0

                    current_in_field = [d for d in components if new_assignments.get(d) == grp]
                    if len(current_in_field) >= n_limit:
                        continue

                    can_take = min(n_limit - len(current_in_field), remaining_slots)
                    if can_take <= 0:
                        continue

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
                    remaining_slots = max(0, remaining_slots - can_take)
                    if remaining_slots == 0:
                        break

        # Stage C: Any drone not assigned yet becomes idle
        for d in components:
            if d not in new_assignments:
                new_assignments[d] = "idle"

        # Stage D: Apply assignments and update memory
        for d, grp in new_assignments.items():
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self._memory_assigned[d] = grp