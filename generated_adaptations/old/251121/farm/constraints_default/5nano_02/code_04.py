from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build a set of valid group names for quick checks
        group_set = set(group_ids)

        # 1) Identify the field with the highest threat level
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            thr = getattr(f, "threat_level", 0.0)
            if thr > max_threat:
                max_threat = thr
                top_field = f
            elif thr == max_threat and top_field is not None:
                # Stable tie-breaker: pick smaller id (if available)
                if getattr(f, "id", "") < getattr(top_field, "id", ""):
                    top_field = f

        # If there is no threat or no valid "idle" group, just bail to a safe fallback
        if top_field is None or getattr(top_field, "threat_level", 0.0) <= 0.0:
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                # Fallback: assign to any available group to satisfy one assignment per drone
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        # 2) Determine the top-field protection group and legality
        group_top = f"protecting {top_field.id}"
        if group_top not in group_set:
            # If we cannot assign to the top-field group, idle all drones as a safe fallback
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        # 3) Compute how many drones are needed for full protection
        required = int(getattr(top_field, "drones_for_full_protection", 0))

        # Count drones currently protecting the top field (based on current read-only state)
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protecting += 1

        needed = max(0, required - current_protecting)

        # 4) Build a one-to-one assignment map (drone -> group)
        assigned = {}

        # 4a) Re-assign drones that are already protecting the top field to the top group (explicit continuity)
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                assigned[d] = group_top

        # 4b) If we still need more, select the closest non-assigned drones to the field center
        if needed > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for d in components:
                if d in assigned:
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
            for i in range(min(needed, len(candidates))):
                _, d = candidates[i]
                assigned[d] = group_top

        # 4c) Assign all remaining drones to idle (or a safe fallback if idle is not available)
        for d in components:
            if d not in assigned:
                if "idle" in group_set:
                    assigned[d] = "idle"
                else:
                    # Fallback: assign to any valid group
                    assigned[d] = next(iter(group_set), None)

        # 5) Apply assignments (one explicit assignment per drone)
        for d, g in assigned.items():
            if g is not None:
                environment.assign_group(d, g)