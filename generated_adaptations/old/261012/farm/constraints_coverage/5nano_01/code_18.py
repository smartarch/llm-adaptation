from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Robust coordinate helper
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

        # Distance between drone and a point
        def dist_to_point(drone, point):
            dx, dy = get_coord(drone)
            return ((dx - point[0]) ** 2 + (dy - point[1]) ** 2) ** 0.5

        # Build list of threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        # If no threat, idle all
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Top-threat field
        top_field = max(threatened_fields, key=lambda f: getattr(f, 'threat_level', 0))
        top_field_id = getattr(top_field, 'id', None)
        top_need = int(getattr(top_field, 'drones_for_full_protection', 0))

        # If cannot require protection or not enough drones, idle all
        if top_need <= 0:
            for d in components:
                environment.assign_group(d, "idle")
            return

        total_drones = len(components)
        if total_drones < top_need:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_center = field_center(top_field)

        # Compute distances to the top field center for all drones
        candidates = []
        for d in components:
            dist = dist_to_point(d, top_center)
            candidates.append((d, dist))

        # Sort by distance and pick the closest top_need drones
        candidates.sort(key=lambda t: t[1])
        chosen_for_top = {d for d, _ in candidates[:top_need]}

        # Assign groups: chosen to protect the top field; others idle
        for d in components:
            if d in chosen_for_top:
                environment.assign_group(d, f"protecting {top_field_id}")
            else:
                environment.assign_group(d, "idle")