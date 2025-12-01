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
            # Fallback: assume tuple-like
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

        # Current protecting drones for the top field
        top_field_id = getattr(top_field, 'id', None)
        current_protecting = [
            d for d in components
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id
        ]
        current_count = len(current_protecting)

        # Drones required for full protection
        full_need = getattr(top_field, 'drones_for_full_protection', 0)

        total_drones = len(components)

        # If we cannot fully protect this field due to not enough drones overall, idle all
        if full_need > total_drones:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # If already fully protected, keep as-is (no partial protection introduced)
        if current_count >= full_need:
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                    other_id = getattr(d, 'target_id')
                    environment.assign_group(d, f"protecting {other_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Otherwise, we attempt to fill to full_need only if possible
        needed = int(full_need) - int(current_count)
        if needed <= 0:
            # Already handled by the early return above, but keep safe
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                    other_id = getattr(d, 'target_id')
                    environment.assign_group(d, f"protecting {other_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Build list of candidate drones not already protecting top field
        candidates = []
        for d in components:
            if not (getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id):
                candidates.append(d)

        # If not enough candidates to reach full_need, we must not partially protect
        if len(candidates) < needed:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Compute distances to the top field center
        top_center = field_center(top_field)
        candidates.sort(key=lambda d: dist_to_point(d, top_center))

        # Select the closest drones to fill the need
        chosen_for_top = candidates[:needed]

        # Now assign groups for all drones
        for d in components:
            # If this drone is chosen to help top field, assign to that protection group
            if d in chosen_for_top:
                environment.assign_group(d, f"protecting {top_field_id}")
                continue

            # If drone is currently protecting another field, keep it in that field's group
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                other_id = getattr(d, 'target_id')
                environment.assign_group(d, f"protecting {other_id}")
                continue

            # Otherwise, assign to idle
            environment.assign_group(d, "idle")