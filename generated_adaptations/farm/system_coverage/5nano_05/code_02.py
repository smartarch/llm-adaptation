from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", [])
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, mark all drones idle
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Identify the top-threat field (highest threat_level)
        top_field = max(threatening_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_field_id = getattr(top_field, "id", None)
        required = getattr(top_field, "drones_for_full_protection", 0)

        # Compute center of the top field
        left = getattr(top_field, "left", 0.0)
        right = getattr(top_field, "right", 0.0)
        top = getattr(top_field, "top", 0.0)
        bottom = getattr(top_field, "bottom", 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Drones currently protecting the TopField
        currently_protecting_ids = [
            d.id for d in components
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field_id
        ]
        current_count = len(currently_protecting_ids)

        needed = max(0, int(required) - current_count)

        # Candidates: drones not already protecting TopField
        candidates = [d for d in components if d.id not in set(currently_protecting_ids)]

        chosen_ids = set()
        if needed > 0 and candidates:
            # Sort candidates by squared distance to top field center
            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                return dx*dx + dy*dy

            candidates.sort(key=lambda d: dist2(d))
            for d in candidates[:needed]:
                chosen_ids.add(d.id)

        # Final grouping: drones protecting TopField (either already or newly chosen) vs idle
        top_protect_ids = set(currently_protecting_ids) | chosen_ids

        for d in components:
            if d.id in top_protect_ids:
                environment.assign_group(d, f"protecting {top_field_id}")
            else:
                environment.assign_group(d, "idle")