from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        fields = getattr(environment, 'fields', [])
        threatened = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        if not threatened:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat_level (desc)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened[0]

        top_group = f"protecting {top_field.id}"
        # Validate top_group exists
        if top_group not in group_ids:
            # If not available, default all to idle
            for d in components:
                environment.assign_group(d, "idle")
            return

        mapping = {}  # drone -> group_id

        # Step 1: assign current top_field protectors to top_group (preserve)
        current_top = [d for d in components
                       if getattr(d, 'state', None) == 'protecting'
                       and getattr(d, 'target_id', None) == top_field.id]
        for d in current_top:
            mapping[d] = top_group

        # Step 2: fill top_field to full protection with closest drones
        current_top_count = len(current_top)
        max_full = getattr(top_field, 'drones_for_full_protection', 0)
        needed = max(0, min(max_full, len(components)) - current_top_count)

        if needed > 0:
            # candidates: drones not already mapped
            candidates = [d for d in components if d not in mapping]
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            def dist_to_top(d):
                loc = getattr(d, 'location', None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, 'x', 0.0) - cx
                dy = getattr(loc, 'y', 0.0) - cy
                return (dx*dx + dy*dy) ** 0.5

            candidates.sort(key=dist_to_top)
            for i in range(min(needed, len(candidates))):
                mapping[candidates[i]] = top_group

        # Step 3: protect other fields fully if enough drones remain
        remaining = [d for d in components if d not in mapping]

        for f in threatened[1:]:
            g_id = f"protecting {f.id}"
            if g_id not in group_ids:
                continue

            # Current capacity for this field (how many are protecting it now)
            current_f = sum(1 for d in components
                            if getattr(d, 'state', None) == 'protecting'
                            and getattr(d, 'target_id', None) == f.id)

            max_for_f = getattr(f, 'drones_for_full_protection', 0)
            needed_f = max(0, min(max_for_f, len(components)) - current_f)

            if needed_f <= 0:
                continue

            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0

            def dist_to_f(d):
                loc = getattr(d, 'location', None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, 'x', 0.0) - cx
                dy = getattr(loc, 'y', 0.0) - cy
                return (dx*dx + dy*dy) ** 0.5

            remaining_sorted = sorted(remaining, key=dist_to_f)
            for i in range(min(needed_f, len(remaining_sorted))):
                d = remaining_sorted[i]
                mapping[d] = g_id
            # update remaining
            remaining = [d for d in remaining if d not in mapping]

        # Step 4: assign the rest: preserve current protections when possible, else idle
        for d in components:
            if d in mapping:
                continue
            if getattr(d, 'state', None) == 'protecting':
                target = getattr(d, 'target_id', None)
                g = f"protecting {target}" if target is not None else None
                if g in group_ids:
                    mapping[d] = g
                    continue
            # Fallback
            mapping[d] = "idle"

        # Apply assignments exactly once per drone
        for d, g in mapping.items():
            environment.assign_group(d, g)