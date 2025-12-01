from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persistent memory of last assigned group per drone (by id)
        # Helps reduce churn: we try to keep drones on the same field if possible.
        self._last_assignment = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Helper: is drone currently protecting a given field (by memory or state)
        def is_protecting_field(d, field_id):
            d_id = id(d)
            last_grp = self._last_assignment.get(d_id, None)
            if last_grp == f"protecting {field_id}":
                return True
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                return True
            return False

        # Helper: current protection count for a field (based on memory + current state)
        def current_protect_count(field):
            count = 0
            for d in components:
                if is_protecting_field(d, field.id):
                    count += 1
            return count

        # Sort fields by threat level descending, then by id for determinism
        fields_sorted = sorted(
            fields,
            key=lambda f: (-getattr(f, "threat_level", 0), getattr(f, "id", "")),
        )

        # Prepare centers for distance calculations
        centers = {f.id: center_of(f) for f in fields_sorted}

        total_drones = len(components)
        half_protection = (total_drones + 1) // 2  # at least half (rounded up)

        # We'll build a fresh assignment for this step
        step_assignment = {}

        # Step 1: Ensure the top-threat field is fully protected
        if fields_sorted:
            top = fields_sorted[0]
            current_top = current_protect_count(top)
            needed_top = max(0, getattr(top, "drones_for_full_protection", 0) - current_top)

            # If any drones are already protecting the top field (memory or state),
            # ensure they are assigned to this field in this step.
            for d in components:
                if is_protecting_field(d, top.id):
                    step_assignment[id(d)] = f"protecting {top.id}"

            if needed_top > 0:
                center_top = centers[top.id]

                # Build candidate drones with priority for those already assigned to this field
                candidates = []
                for d in components:
                    d_id = id(d)
                    if d_id in step_assignment:
                        # Already assigned to top in this step; skip in candidate pool
                        continue
                    last_grp = self._last_assignment.get(d_id, None)
                    priority = 0 if (last_grp == f"protecting {top.id}") or (
                        getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id
                    ) else 1
                    lx = getattr(d, "location").x
                    ly = getattr(d, "location").y
                    dist2 = (lx - center_top[0]) ** 2 + (ly - center_top[1]) ** 2
                    candidates.append((priority, dist2, d))
                candidates.sort(key=lambda t: (t[0], t[1]))

                assigned = 0
                for _, _, d in candidates:
                    if assigned >= needed_top:
                        break
                    step_assignment[id(d)] = f"protecting {top.id}"
                    assigned += 1

        # Step 2: Use remaining drones to protect subsequent fields if we can reach the half-protection goal
        if fields_sorted:
            # Compute current protected count for all fields based on step_assignment and memory/state
            def protected_count_for_field(field):
                count = 0
                for d in components:
                    d_id = id(d)
                    if step_assignment.get(d_id, None) == f"protecting {field.id}":
                        count += 1
                    elif is_protecting_field(d, field.id):
                        count += 1
                return count

            for f in fields_sorted[1:]:
                current = protected_count_for_field(f)
                needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
                if needed <= 0:
                    continue
                # If adding this field would make total protected drones exceed half, still attempt to protect
                # as long as we can fully protect this field.

                # If we already meet the half-protection goal, do not allocate further (to avoid churn unnecessarily)
                # However, we should still aim to protect as many high-threat fields as possible.
                if sum(1 for d in components if step_assignment.get(id(d), None) and step_assignment[id(d)].startswith("protecting")) < half_protection:
                    pass  # we are allowed to allocate more to reach half protection

                center_f = centers[f.id]

                # Build candidates not yet assigned
                candidates = []
                for d in components:
                    d_id = id(d)
                    if d_id in step_assignment:
                        continue
                    last_grp = self._last_assignment.get(d_id, None)
                    priority = 0 if (last_grp == f"protecting {f.id}") or (
                        getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
                    ) else 1
                    lx = getattr(d, "location").x
                    ly = getattr(d, "location").y
                    dist2 = (lx - center_f[0]) ** 2 + (ly - center_f[1]) ** 2
                    candidates.append((priority, dist2, d))
                candidates.sort(key=lambda t: (t[0], t[1]))

                assigned = 0
                for _, _, d in candidates:
                    if assigned >= needed:
                        break
                    step_assignment[id(d)] = f"protecting {f.id}"
                    assigned += 1

        # Step 3: All remaining drones go idle
        for d in components:
            if id(d) not in step_assignment:
                step_assignment[id(d)] = "idle"

        # Apply the assignments to the environment
        for d in components:
            environment.assign_group(d, step_assignment[id(d)])

        # Persist this step's assignments for the next step
        self._last_assignment = step_assignment