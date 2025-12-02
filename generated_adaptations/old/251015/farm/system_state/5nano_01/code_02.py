from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with a positive threat level
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        if not threat_fields:
            # No threat: all drones idle
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat
        top_field = max(threat_fields, key=lambda f: getattr(f, 'threat_level', 0.0))
        field_id = top_field.id

        # Compute field center
        left = getattr(top_field, 'left', 0.0)
        right = getattr(top_field, 'right', 0.0)
        top = getattr(top_field, 'top', 0.0)
        bottom = getattr(top_field, 'bottom', 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Drones currently protecting this field should be kept
        keepers = []
        for d in components:
            if getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) == field_id:
                keepers.append(d)

        # Drones needed to reach full protection
        required = getattr(top_field, 'drones_for_full_protection', 0)
        extras_needed = max(0, int(required) - len(keepers))

        # Candidates are drones not already kept as protectors
        candidates = [d for d in components if d not in keepers]

        # Compute distances to the field center for ordering
        dist_pairs = []
        for d in candidates:
            loc = getattr(d, 'location', None)
            if loc is None:
                dx = dy = 0.0
            else:
                dx = getattr(loc, 'x', 0.0) - center_x
                dy = getattr(loc, 'y', 0.0) - center_y
            dist2 = dx*dx + dy*dy
            dist_pairs.append((dist2, d))
        dist_pairs.sort(key=lambda t: t[0])

        # Choose the closest extras_needed drones
        extras = [d for _, d in dist_pairs[:min(len(dist_pairs), extras_needed)]]

        # Assign groups
        # Keepers + extras protect the top field
        protected_set = set(keepers) | set(extras)
        for d in components:
            if d in protected_set:
                environment.assign_group(d, f"protecting {field_id}")
            else:
                environment.assign_group(d, "idle")