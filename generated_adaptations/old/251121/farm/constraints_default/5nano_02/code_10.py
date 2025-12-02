from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        group_set = set(group_ids)

        # 1) Identify the field with the highest threat
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            thr = getattr(f, "threat_level", 0.0)
            if thr > max_threat:
                max_threat = thr
                top_field = f
            elif thr == max_threat and top_field is not None:
                if getattr(f, "id", "") < getattr(top_field, "id", ""):
                    top_field = f

        # If no threat, idle all (fallback if needed)
        if top_field is None or getattr(top_field, "threat_level", 0.0) <= 0.0:
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        group_top = f"protecting {top_field.id}"
        if group_top not in group_set:
            # If we cannot assign to the top-field group, idle all (fallback)
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        # 2) How many drones are needed for full protection?
        required = int(getattr(top_field, "drones_for_full_protection", 0))

        # 3) Current protection of the top field
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protecting += 1

        needed_full = max(0, required - current_protecting)

        # 4) Build a single explicit assignment map
        assigned = {}

        # 4a) Continuity: drones already protecting the top field stay in it
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                assigned[d] = group_top

        # 4b) If more are needed for full protection, pick closest non-assigned drones
        if needed_full > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for d in components:
                if d in assigned:
                    continue
                # Only consider non-protecting drones to avoid moving drones currently protecting other fields
                if getattr(d, "state", None) == "protecting":
                    # skip drones protecting other fields
                    if getattr(d, "target_id", None) != top_field.id:
                        continue
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])
            for i in range(min(needed_full, len(candidates))):
                _, d = candidates[i]
                assigned[d] = group_top

        # 4c) Ensure at least half of drones are protecting the top field
        total = len(components)
        half_needed = (total + 1) // 2
        currently_in_top = sum(1 for d, g in assigned.items() if g == group_top)

        if currently_in_top < half_needed:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Consider only non-protecting drones (idle or moving) to reach half
            candidates = []
            for d in components:
                if d in assigned:
                    continue
                if getattr(d, "state", None) == "protecting":
                    # skip drones protecting other fields
                    if getattr(d, "target_id", None) is not None and getattr(d, "target_id", None) != top_field.id:
                        continue
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])
            for dist2, d in candidates:
                if sum(1 for gg in assigned.values() if gg == group_top) >= half_needed:
                    break
                if d not in assigned:
                    assigned[d] = group_top

        # 4d) Remaining drones -> idle or fallback group
        for d in components:
            if d not in assigned:
                if "idle" in group_set:
                    assigned[d] = "idle"
                else:
                    assigned[d] = next(iter(group_set), None)

        # 5) Apply assignments (exactly one per drone)
        for d, g in assigned.items():
            if g is not None:
                environment.assign_group(d, g)