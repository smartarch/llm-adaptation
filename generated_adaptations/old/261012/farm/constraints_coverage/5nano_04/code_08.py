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

        # If no threat fields, idle all drones
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

        # Assigned map: drone -> group_name
        assigned = {}

        # Step 1: Top field protection (fully protect the most threatened field)
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

        # Assign the closest drones to the top field
        for i in range(min(top_need, len(dist_list))):
            assigned[dist_list[i][1]] = top_group

        # Step 2: Allocate drones to remaining threatened fields
        for f in threat_fields_sorted[1:]:
            fid = f.id
            group_name = field_group[fid]
            center = centers[fid]
            need = required[fid]

            # Current drones already protecting this field
            current = [d for d, g in assigned.items() if g == group_name]

            if len(current) > need:
                # Reallocate extras away (to idle)
                dist_to_center = []
                for d in current:
                    dist_to_center.append((dist2(get_coords(d), center), d))
                dist_to_center.sort(key=lambda t: t[0], reverse=True)
                extras = [pair[1] for pair in dist_to_center[: len(current) - need]]
                for d in extras:
                    assigned[d] = "idle"
                # Remaining stay on this field
                for _, d in dist_to_center[len(current) - need:]:
                    assigned[d] = group_name
            elif len(current) < need:
                need_more = need - len(current)
                # Pool: any drone not currently protecting this field
                pool = [d for d in components if assigned.get(d) != group_name]
                pool_with_dist = []
                for d in pool:
                    pool_with_dist.append((dist2(get_coords(d), center), d))
                pool_with_dist.sort(key=lambda t: t[0])
                for i in range(min(need_more, len(pool_with_dist))):
                    d = pool_with_dist[i][1]
                    assigned[d] = group_name
            else:
                # Already fully protected; ensure all are assigned to this field
                for d in current:
                    assigned[d] = group_name

        # Step 3: Idle any drones not assigned yet
        for d in components:
            if d not in assigned:
                assigned[d] = "idle"

        # Apply assignments (explicitly re-assigning even if same group)
        for d in components:
            group = assigned.get(d, "idle")
            if group not in group_ids:
                group = "idle"
            environment.assign_group(d, group)