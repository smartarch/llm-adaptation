from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to get coordinates robustly
        def get_coord(obj):
            loc = getattr(obj, 'location', None)
            if loc is None:
                return (0.0, 0.0)
            if hasattr(loc, 'x') and hasattr(loc, 'y'):
                return (float(loc.x), float(loc.y))
            try:
                return (float(loc[0]), float(loc[1]))
            except Exception:
                return (0.0, 0.0)

        # Compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Distance between drone location and a point
        def dist_to_point(drone, point):
            dx, dy = get_coord(drone)
            return ((dx - point[0]) ** 2 + (dy - point[1]) ** 2) ** 0.5

        # Build list of fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        # If no threat, idle all
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the top-threat field (tie-breaking by first occurrence)
        top_field = max(threatened_fields, key=lambda f: getattr(f, 'threat_level', 0))
        top_field_id = getattr(top_field, 'id', None)

        # Current protection count for the top field
        current_top = sum(
            1 for d in components
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id
        )

        # Drones required for full protection for the top field
        top_need = int(getattr(top_field, 'drones_for_full_protection', 0))

        # If top field already fully protected, keep protections as-is (move others to their current groups)
        if current_top >= top_need:
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                    other_id = getattr(d, 'target_id')
                    environment.assign_group(d, f"protecting {other_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # If cannot be fully protected due to zero need, or top_need is zero
        if top_need <= 0:
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                    other_id = getattr(d, 'target_id')
                    environment.assign_group(d, f"protecting {other_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Otherwise, we try to fully protect the top field by assigning the closest drones
        needed = top_need - current_top

        # Build candidate pool: drones not currently protecting the top field
        candidates = [d for d in components if not (getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id)]

        # If not enough candidates (shouldn't happen if total >= top_need), idle all to avoid partial protection
        if len(candidates) < needed:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Compute distance to top field center
        top_center = field_center(top_field)
        candidates.sort(key=lambda d: dist_to_point(d, top_center))

        chosen_for_top = candidates[:needed]

        # Now assign groups
        for d in components:
            if d in chosen_for_top:
                environment.assign_group(d, f"protecting {top_field_id}")
                continue

            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                other_id = getattr(d, 'target_id')
                environment.assign_group(d, f"protecting {other_id}")
                continue

            environment.assign_group(d, "idle")