from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # 3) Current protect counts for each field
        current_counts = {f.id: 0 for f in fields_sorted}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tgt = getattr(d, "target_id", None)
                if tgt in current_counts:
                    current_counts[tgt] += 1

        # 4) Track allocations
        unallocated = list(components)  # drones not yet assigned to a protecting group in this step
        allocated = set()

        # 5) Greedily allocate drones to each field in priority order
        for f in fields_sorted:
            field_id = f.id
            protect_group = f"protecting {field_id}"
            if protect_group not in group_ids:
                # Cannot assign to this field's protect group; skip allocations for this field
                continue

            current = current_counts.get(field_id, 0)
            needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current)
            if needed <= 0:
                continue  # already fully protected

            if not unallocated:
                break  # no drones left to allocate

            # Field center
            left = getattr(f, "left", 0.0)
            right = getattr(f, "right", 0.0)
            top = getattr(f, "top", 0.0)
            bottom = getattr(f, "bottom", 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            # Distance to field center (squared, to avoid sqrt)
            def dist_sq(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return dx * dx + dy * dy

            unallocated.sort(key=dist_sq)

            take = min(needed, len(unallocated))
            chosen = unallocated[:take]

            for d in chosen:
                environment.assign_group(d, protect_group)
                allocated.add(d)

            # Update pool
            unallocated = unallocated[take:]

            # Update count after allocation
            current_counts[field_id] = current_counts.get(field_id, 0) + take

        # 6) Any remaining drones go idle
        for d in list(components):
            if d not in allocated:
                environment.assign_group(d, "idle")