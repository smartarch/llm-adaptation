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

        # Prepare mappings and helpers
        threat_sorted = sorted(threatened, key=lambda f: f.threat_level, reverse=True)
        top_field = threat_sorted[0]
        top_group = f"protecting {top_field.id}"

        # Ensure top_group exists
        if top_group not in group_ids:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Build quick index: field_id -> field_object
        fields_by_id = {f.id: f for f in fields}

        # Current protection counts per field
        current_prot = {}
        for f in fields:
            current_prot[f.id] = 0
        for d in components:
            if getattr(d, 'state', None) == 'protecting':
                tid = getattr(d, 'target_id', None)
                if tid in current_prot:
                    current_prot[tid] += 1

        # Helper: get drones_for_full_protection for a field (default 0 if unknown)
        def full_needed(field_id):
            f = fields_by_id.get(field_id)
            if f is None:
                return 0
            return getattr(f, 'drones_for_full_protection', 0)

        # Step 1: Preserve drones already protecting the top field
        mapping = {}
        top_current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field.id]
        for d in top_current:
            mapping[d] = top_group

        # Step 2: Fill top_field to full protection using closest candidates
        current_top_count = len(top_current)
        max_full_top = min(full_needed(top_field.id), len(components))
        needed_top = max(0, max_full_top - current_top_count)

        if needed_top > 0:
            # Candidates: not already mapped and not protecting a fully protected field
            candidates = []
            for d in components:
                if d in mapping:
                    continue
                st = getattr(d, 'state', None)
                if st == 'protecting':
                    tgd = getattr(d, 'target_id', None)
                    # If the field the drone protects is fully protected, do not move it
                    if current_prot.get(tgd, 0) >= full_needed(tgd):
                        continue
                candidates.append(d)

            # Sort candidates by distance to top_field center
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
            for i in range(min(needed_top, len(candidates))):
                mapping[candidates[i]] = top_group

        # Step 3: Consider protecting other threatened fields if we have spare drones
        remaining = [d for d in components if d not in mapping]

        for f in threat_sorted[1:]:
            g_id = f"protecting {f.id}"
            if g_id not in group_ids:
                continue

            # Current protection for this field
            current_f = current_prot.get(f.id, 0)
            max_for_f = full_needed(f.id)
            needed_f = max(0, max_for_f - current_f)
            if needed_f <= 0:
                continue

            # Gather candidates from remaining, preferring those not protecting fully-protected fields
            candidates_f = []
            for d in remaining:
                st = getattr(d, 'state', None)
                if st == 'protecting':
                    tgd = getattr(d, 'target_id', None)
                    if current_prot.get(tgd, 0) >= full_needed(tgd):
                        continue
                candidates_f.append(d)

            if not candidates_f:
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

            candidates_f.sort(key=dist_to_f)
            take = min(needed_f, len(candidates_f))
            for i in range(take):
                mapping[candidates_f[i]] = g_id

            # Update remaining
            remaining = [d for d in remaining if d not in mapping]

        # Step 4: Assign remaining drones
        for d in components:
            if d in mapping:
                continue
            # If currently protecting a field and that field group exists, keep it
            if getattr(d, 'state', None) == 'protecting':
                tid = getattr(d, 'target_id', None)
                g = f"protecting {tid}" if tid is not None else None
                if g in group_ids:
                    mapping[d] = g
                    continue
            # Otherwise, idle
            mapping[d] = "idle"

        # Apply assignments exactly once per drone
        for d, g in mapping.items():
            environment.assign_group(d, g)