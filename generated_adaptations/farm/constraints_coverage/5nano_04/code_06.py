from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def get_coords(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return (0.0, 0.0)
            x = getattr(loc, "x", None)
            y = getattr(loc, "y", None)
            try:
                return (float(x), float(y))
            except Exception:
                return (0.0, 0.0)

        def dist2(p, q):
            dx = p[0] - q[0]
            dy = p[1] - q[1]
            return dx * dx + dy * dy

        # Gather threat fields
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (high to low)
        threat_fields_sorted = sorted(threat_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Precompute centers and required drones for each field
        centers = {f.id: field_center(f) for f in threat_fields_sorted}
        required = {f.id: max(1, int(getattr(f, "drones_for_full_protection", 1)))
                    for f in threat_fields_sorted}
        field_group = {f.id: f"protecting {f.id}" for f in threat_fields_sorted}

        # Assign drones to fields by proximity, respecting priority
        assigned = {}  # drone -> group_name

        # Top field first
        top = threat_fields_sorted[0]
        top_id = top.id
        top_center = centers[top_id]
        top_group = field_group[top_id]
        top_need = required[top_id]

        # Distances from all drones to top center
        dist_list = []
        for d in components:
            dist_list.append((dist2(get_coords(d), top_center), d))
        dist_list.sort(key=lambda t: t[0])

        for i in range(min(top_need, len(dist_list))):
            assigned[dist_list[i][1]] = top_group

        # Remaining fields (in threat order)
        for f in threat_fields_sorted[1:]:
            fid = f.id
            group = field_group[fid]
            need = required[fid]

            # Build list of drones not yet assigned to a higher-priority field
            available = [(dist2(get_coords(d), centers[fid]), d)
                         for d in components if d not in assigned.values()]

            available.sort(key=lambda t: t[0])

            for i in range(min(need, len(available))):
                assigned[available[i][1]] = group

        # Step 3: idle any drones not assigned
        for d in components:
            if d not in assigned:
                assigned[d] = "idle"

        # Apply assignments (explicitly re-assigning even if same group)
        for d in components:
            group = assigned.get(d, "idle")
            if group not in group_ids:
                group = "idle"
            environment.assign_group(d, group)