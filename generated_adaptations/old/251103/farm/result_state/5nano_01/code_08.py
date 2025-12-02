from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 0) Gather fields with positive threat levels
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper: compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # 1) Build a prioritized list of fields by threat, tie-broken by proximity to the nearest drone
        field_info = []
        for f in fields:
            cx, cy = center_of(f)
            min_dist = float("inf")
            for d in components:
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < min_dist:
                    min_dist = dist
            field_info.append((f, f.threat_level, min_dist))

        field_info.sort(key=lambda t: (-t[1], t[2]))  # sort by threat desc, then proximity

        # Helper to get the protecting group name for a field
        def group_name(field):
            return f"protecting {field.id}"

        top_field = field_info[0][0]
        top_group = group_name(top_field)
        if top_group not in group_ids:
            # Fallback: if we can't create the required group, idle all
            for d in components:
                environment.assign_group(d, "idle")
            return

        assigned_indices = set()

        # 2) Iterate over fields in priority order and fully protect as many as possible
        for f, _, _ in field_info:
            g_name = group_name(f)
            if g_name not in group_ids:
                continue

            # Drones currently targeting this field (protecting or en route)
            current_for_field = []
            for idx, d in enumerate(components):
                if getattr(d, "target_id", None) == f.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                    current_for_field.append(idx)

            # Ensure these drones are grouped for this field
            for idx in current_for_field:
                environment.assign_group(components[idx], g_name)
            assigned_indices.update(current_for_field)

            required = int(getattr(f, "drones_for_full_protection", 0))
            current_count = len(current_for_field)
            needed = max(0, required - current_count)

            if needed <= 0:
                continue

            # Collect closest available drones to fill the gap
            cx, cy = center_of(f)
            candidates = []
            for idx, d in enumerate(components):
                if idx in assigned_indices:
                    continue
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, idx))

            candidates.sort()
            for i in range(min(needed, len(candidates))):
                idx = candidates[i][1]
                environment.assign_group(components[idx], g_name)
                assigned_indices.add(idx)

        # 3) Remaining drones go idle
        for idx, d in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(d, "idle")