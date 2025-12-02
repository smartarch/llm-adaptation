from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist2(drone, x, y):
            dx = getattr(drone.location, "x", 0.0) - x
            dy = getattr(drone.location, "y", 0.0) - y
            return dx * dx + dy * dy

        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat_level (desc), stable by id
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
            reverse=True,
        )

        top_field = threat_fields_sorted[0]
        top_field_id = getattr(top_field, "id", None)
        top_center_x, top_center_y = field_center(top_field)

        # Current drones protecting the top field
        current_top_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id
        ]

        drones_for_top = getattr(top_field, "drones_for_full_protection", 0)
        need_top = max(0, int(drones_for_top) - int(len(current_top_protecting)))

        top_group = f"protecting {top_field_id}"
        top_group_valid = top_group in set(group_ids)

        # Build the set of drones that will protect the top field
        top_protecting = list(current_top_protecting)

        if need_top > 0:
            # From all drones, pick the closest ones not already protecting the top field
            not_already = [d for d in components if d not in top_protecting]
            not_already.sort(key=lambda d: dist2(d, top_center_x, top_center_y))
            for d in not_already[:need_top]:
                top_protecting.append(d)

        # Assign groups for all drones
        for d in components:
            if d in top_protecting:
                if top_group_valid:
                    environment.assign_group(d, top_group)
                else:
                    environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, "idle")