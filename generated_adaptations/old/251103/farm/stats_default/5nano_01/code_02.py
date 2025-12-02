from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Determine the field with the highest threat level (>0)
        target_field = None
        max_threat = -1.0

        for f in environment.fields:
            # Fields have attributes: id, left, top, right, bottom, threat_level, drones_for_full_protection
            if getattr(f, "threat_level", 0) > 0:
                if getattr(f, "threat_level", 0) > max_threat:
                    max_threat = getattr(f, "threat_level", 0)
                    target_field = f

        # If no threats, idle all drones
        if target_field is None:
            idle_group = "idle"
            if idle_group not in group_ids:
                # Fallback: if idle group name isn't valid, assign to the first valid group
                idle_group = group_ids[0] if group_ids else None
            for d in components:
                if idle_group is not None:
                    environment.assign_group(d, idle_group)
            return

        # Target field center
        cx = (target_field.left + target_field.right) / 2.0
        cy = (target_field.top + target_field.bottom) / 2.0

        # Drones required for full protection
        drones_needed = int(getattr(target_field, "drones_for_full_protection", 0) or 0)

        # If no drones are required for full protection, just idle all
        protecting_group = f"protecting {target_field.id}"
        if protecting_group not in group_ids:
            # If the specific protecting group isn't valid, treat as idle
            idle_group = "idle"
            if idle_group not in group_ids:
                idle_group = group_ids[0] if group_ids else None
            for d in components:
                if idle_group is not None:
                    environment.assign_group(d, idle_group)
            return

        # Compute distances (squared distance to avoid sqrt)
        drones_with_dist = []
        for d in components:
            loc = getattr(d, "location", None)
            if loc is None:
                # If location not available, treat as far away
                dist2 = float('inf')
            else:
                dx = loc.x - cx
                dy = loc.y - cy
                dist2 = dx * dx + dy * dy
            drones_with_dist.append((dist2, d))

        # Sort by distance (closest first)
        drones_with_dist.sort(key=lambda t: t[0])

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else None

        # Assign the closest drones to protecting the top-threat field, rest to idle
        assigned = 0
        for dist2, d in drones_with_dist:
            if assigned < drones_needed:
                environment.assign_group(d, protecting_group)
                assigned += 1
            else:
                if idle_group is not None:
                    environment.assign_group(d, idle_group)