from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Pick the most threatened field
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threat_fields[0]
        top_id = top_field.id

        # Helper: field center
        def center(field):
            cx = (getattr(field, "left", 0.0) + getattr(field, "right", 0.0)) / 2.0
            cy = (getattr(field, "top", 0.0) + getattr(field, "bottom", 0.0)) / 2.0
            return cx, cy

        # Current protection mapping (to know who is protecting what)
        allocated_by_field = {f.id: [] for f in threat_fields}
        drone_owner = [None] * len(components)  # field_id each drone is protecting, or None
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in allocated_by_field:
                    allocated_by_field[tid].append(idx)
                    drone_owner[idx] = tid

        # Determine how many drones are required for full protection of the top field
        required = int(getattr(top_field, "drones_for_full_protection", 1))
        if required < 0:
            required = 0

        # Current drones protecting the top field
        current_top = allocated_by_field.get(top_id, [])
        need = max(0, required - len(current_top))

        # If we need more drones, pick the closest available drones to the top field
        if need > 0:
            top_center = center(top_field)
            candidates = []
            for idx, d in enumerate(components):
                if drone_owner[idx] == top_id:
                    continue  # already protecting top
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - top_center[0]
                    dy = getattr(loc, "y", 0.0) - top_center[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                candidates.append((dist, idx))

            candidates.sort(key=lambda t: t[0])
            to_move = [idx for _, idx in candidates[:need]]

            for idx in to_move:
                # Remove from previous field if needed
                prev_field = drone_owner[idx]
                if prev_field is not None and prev_field in allocated_by_field:
                    if idx in allocated_by_field[prev_field]:
                        allocated_by_field[prev_field].remove(idx)
                # Assign to top field
                allocated_by_field[top_id].append(idx)
                drone_owner[idx] = top_id

        # Final assignment: all drones either protect the top field or are idle
        for idx, d in enumerate(components):
            owner = drone_owner[idx]
            if owner is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {owner}")