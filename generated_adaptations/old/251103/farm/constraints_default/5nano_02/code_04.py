from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: squared distance from drone location to a point
        def dist2(drone, x, y):
            dx = getattr(drone.location, "x", 0.0) - x
            dy = getattr(drone.location, "y", 0.0) - y
            return dx * dx + dy * dy

        # Gather fields with positive threat level
        fields_with_threat = [
            f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0
        ]

        # If no threatened fields, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first). If equal, deterministic by id.
        fields_sorted = sorted(
            fields_with_threat,
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
            reverse=True,
        )

        # Top field to protect
        top_field = fields_sorted[0]
        top_field_id = getattr(top_field, "id", None)
        top_center_x, top_center_y = field_center(top_field)

        # Number of drones required for full protection of the top field
        drones_for_top = getattr(top_field, "drones_for_full_protection", 0)

        # Current number of drones protecting the top field
        current_top_protecting = sum(
            1
            for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id
        )

        need_top = max(0, int(drones_for_top) - int(current_top_protecting))

        # Build a set of drones that will protect the top field
        top_set = set()

        # Add currently protecting drones for the top field
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                top_set.add(d)

        # If more drones are needed, pick the closest among those not already protecting the top field
        if need_top > 0:
            candidates = [d for d in components if d not in top_set]
            candidates.sort(key=lambda d: dist2(d, top_center_x, top_center_y))
            for d in candidates[:need_top]:
                top_set.add(d)

        # Assign groups
        for d in components:
            if d in top_set:
                environment.assign_group(d, f"protecting {top_field_id}")
            else:
                # If currently protecting some field, try to keep that protection if the field still has threat
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                    tgt = d.target_id
                    target_field = next((f for f in getattr(environment, "fields", []) if getattr(f, "id", None) == tgt), None)
                    if target_field is not None and getattr(target_field, "threat_level", 0) > 0:
                        environment.assign_group(d, f"protecting {tgt}")
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")