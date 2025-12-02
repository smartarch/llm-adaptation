from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            thr = getattr(f, "threat_level", 0.0)
            if thr > max_threat:
                max_threat = thr
                top_field = f
            elif thr == max_threat and top_field is not None:
                # Tie-breaker: pick field with smaller id (stable choice)
                if f.id < top_field.id:
                    top_field = f

        # If there is no threat, idle all drones
        if top_field is None or getattr(top_field, "threat_level", 0.0) <= 0.0:
            if "idle" in group_ids:
                for d in components:
                    environment.assign_group(d, "idle")
            return

        # Determine the top field's protection requirements
        required = getattr(top_field, "drones_for_full_protection", 0)

        # Count how many drones are already protecting the top field
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protecting += 1

        needed = max(0, int(required) - int(current_protecting))

        group_top = f"protecting {top_field.id}"
        top_group_exists = group_top in group_ids

        if needed > 0 and top_group_exists:
            # Compute field center for distance measurement
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Build list of candidate drones not already protecting the top field
            candidates = []
            for d in components:
                if getattr(d, "target_id", None) != top_field.id:
                    loc = getattr(d, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist2 = dx*dx + dy*dy
                    else:
                        dist2 = float('inf')
                    candidates.append((dist2, d))

            # Sort by distance and assign closest drones
            candidates.sort(key=lambda t: t[0])
            assigned = 0
            for dist2, d in candidates:
                if assigned >= needed:
                    break
                environment.assign_group(d, group_top)
                assigned += 1

        # Finally, ensure all drones not protecting the top field are idle (if an idle group exists)
        if "idle" in group_ids:
            for d in components:
                if getattr(d, "target_id", None) != top_field.id:
                    environment.assign_group(d, "idle")