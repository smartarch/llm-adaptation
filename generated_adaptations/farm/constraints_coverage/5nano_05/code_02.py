from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields and identify those with threat
        fields = list(environment.fields)
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat level
        target_field = max(threatened, key=lambda f: getattr(f, "threat_level", 0))

        # Determine how many drones are needed for full protection
        required = getattr(target_field, "drones_for_full_protection", len(components))
        if not isinstance(required, int) or required < 0:
            required = len(components)

        # Compute field center (approximate)
        left = getattr(target_field, "left", 0.0)
        right = getattr(target_field, "right", 0.0)
        top = getattr(target_field, "top", 0.0)
        bottom = getattr(target_field, "bottom", 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Rank drones by distance to the field center
        def dist2(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - center_x
            dy = getattr(loc, "y", 0.0) - center_y
            return dx * dx + dy * dy

        drones_sorted = sorted(components, key=dist2)

        # Select closest drones for protection
        needed = max(0, min(required, len(drones_sorted)))
        protect_list = drones_sorted[:needed]
        protect_ids = set(id(d) for d in protect_list)

        # Assign groups: protecting target_field for selected drones, idle for others
        for c in components:
            if id(c) in protect_ids:
                environment.assign_group(c, f"protecting {target_field.id}")
            else:
                environment.assign_group(c, "idle")