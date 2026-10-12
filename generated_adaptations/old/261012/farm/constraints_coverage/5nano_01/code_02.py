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
        current_protecting = [
            d for d in components
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == getattr(top_field, 'id', None)
        ]
        current_count = len(current_protecting)

        # Drones needed for full protection
        full_need = getattr(top_field, 'drones_for_full_protection', 0)
        needed = max(0, int(full_need) - int(current_count))

        # If field already fully protected, we still keep drones there (handled by re-assignment)
        # Gather candidate drones to assist top field: any drone that is not currently protecting top_field
        top_field_id = getattr(top_field, 'id', None)
        candidates = []
        for d in components:
            if not (getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id):
                candidates.append(d)

        # Compute distances from each candidate to the top field center
        top_center = field_center(top_field)
        candidates.sort(key=lambda d: dist_to_point(d, top_center))

        # Select the closest drones to fill the need
        chosen_for_top = candidates[:needed] if needed > 0 else []

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