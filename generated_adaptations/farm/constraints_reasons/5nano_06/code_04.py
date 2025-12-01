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

        # Map field id to its protection group name
        field_to_group = {f.id: f"protecting {f.id}" for f in fields_sorted}

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

        # New assignments for this step
        new_assignments = {}

        # Stage A: Fully protect the primary field
        if primary_field:
            # Drones currently protecting the primary (from memory)
            currently_primary = [d for d in components if self._memory_assigned.get(d) == primary_group]

            n_needed = getattr(primary_field, "drones_for_full_protection", 0)
            if n_needed is None:
                n_needed = 0

            # Keep the best drones among those already protecting primary, up to n_needed
            primary_kept = []
            if currently_primary and n_needed > 0:
                distances = [(dist_to_field(d, primary_field), d) for d in currently_primary]
                distances.sort(key=lambda t: t[0])
                primary_kept = [d for _, d in distances[:n_needed]]

            # Assign kept drones to primary group
            for d in primary_kept:
                new_assignments[d] = primary_group

            # If more drones are needed to reach n_needed, pick closest among remaining
            need_more = max(0, n_needed - len(primary_kept))
            if need_more > 0:
                candidates = []
                for d in components:
                    if new_assignments.get(d) == primary_group:
                        continue
                    # distance to primary field
                    dist = dist_to_field(d, primary_field)
                    candidates.append((dist, d))
                candidates.sort(key=lambda t: t[0])
                for i in range(min(need_more, len(candidates))):
                    _, d = candidates[i]
                    new_assignments[d] = primary_group

        # Stage B: Only allocate to other fields if primary field is fully protected
        # Count how many drones are protecting (non-idle)
        total_protecting_now = sum(1 for d in components if new_assignments.get(d, None) and new_assignments[d] != "idle")
        if primary_field and len([d for d in new_assignments if new_assignments[d] == primary_group]) == getattr(primary_field, "drones_for_full_protection", 0):
            # Primary is fully protected; ensure at least half drones are protecting something
            if total_protecting_now < half:
                remaining_slots = half - total_protecting_now
                for field in fields_sorted[1:]:
                    grp = f"protecting {field.id}"
                    n_limit = getattr(field, "drones_for_full_protection", 0)
                    if n_limit is None:
                        n_limit = 0

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