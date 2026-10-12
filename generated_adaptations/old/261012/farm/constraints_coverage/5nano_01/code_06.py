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
        top_field_id = getattr(top_field, 'id', None)

        # Current protection counts per field
        current_counts = {}
        for f in environment.fields:
            if getattr(f, 'threat_level', 0) > 0:
                fid = getattr(f, 'id', None)
                # count drones protecting this field
                cnt = sum(1 for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == fid)
                current_counts[fid] = cnt

        # Drones required for full protection for each field
        full_need = {getattr(f, 'id', None): getattr(f, 'drones_for_full_protection', 0) for f in environment.fields if getattr(f, 'threat_level', 0) > 0}
        top_need = int(full_need.get(top_field_id, 0))
        current_top = int(current_counts.get(top_field_id, 0))

        # If top field is already fully protected, keep protections
        if current_top >= top_need:
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                    other_id = getattr(d, 'target_id')
                    environment.assign_group(d, f"protecting {other_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Compute total drones and needed drones for top field
        total_drones = len(components)
        needed = top_need - current_top

        # Compute spare drones per other field (without breaking full protection)
        spare_per_field = {}
        for fid, count in current_counts.items():
            if fid == top_field_id:
                continue
            spare = max(0, count - int(full_need.get(fid, 0)))
            spare_per_field[fid] = spare

        # Total spare available from other fields
        total_spare = sum(spare_per_field.values()) if spare_per_field else 0

        # Number of idle drones (not currently protecting any field)
        idle_drone_count = sum(1 for d in components if getattr(d, 'state', None) != 'protecting')

        # If not enough spare to cover needed (including idles as potential), idle all
        if total_spare + idle_drone_count < needed:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Build candidate pool: drones not protecting top_field
        top_center = field_center(top_field)
        candidates = []
        for d in components:
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field_id:
                # cannot move from top field
                continue
            # If drone is protecting some other field, only consider if that field has spare
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                other_id = getattr(d, 'target_id')
                if spare_per_field.get(other_id, 0) <= 0:
                    continue
                dist = dist_to_point(d, top_center)
                candidates.append((d, dist, other_id))
            else:
                # Idle or in-transit (not protecting any field)
                dist = dist_to_point(d, top_center)
                candidates.append((d, dist, None))

        # If not enough candidates to fulfill needed, idle all
        if len(candidates) < needed:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort candidates by distance to top field
        candidates.sort(key=lambda t: t[1])

        # Select closest candidates while respecting per-field spare limits
        chosen_for_top = []
        chosen_from_field = {fid: 0 for fid in spare_per_field.keys()}
        for d, _, other in candidates:
            if len(chosen_for_top) >= needed:
                break
            if other is None:
                # Idle candidate, can take freely
                chosen_for_top.append(d)
            else:
                if chosen_from_field.get(other, 0) < spare_per_field.get(other, 0):
                    chosen_for_top.append(d)
                    chosen_from_field[other] += 1

        if len(chosen_for_top) < needed:
            # Not enough candidates without breaking protections
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Assign groups
        for d in components:
            if d in chosen_for_top:
                environment.assign_group(d, f"protecting {top_field_id}")
                continue

            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                other_id = getattr(d, 'target_id')
                environment.assign_group(d, f"protecting {other_id}")
                continue

            environment.assign_group(d, "idle")