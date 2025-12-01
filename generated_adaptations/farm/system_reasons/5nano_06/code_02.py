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
        top_group_valid = top_group in group_ids

        # Count how many drones are currently protecting the top field
        def _drone_target_field(d):
            return getattr(d, 'target_id', None)

        def _drone_state(d):
            return getattr(d, 'state', None)

        current_top = 0
        for d in components:
            if _drone_state(d) == 'protecting' and _drone_target_field(d) == top_field.id:
                current_top += 1

        # How many drones can we assign to fully protect the top field?
        max_full = min(getattr(top_field, 'drones_for_full_protection', 0), len(components))
        need_top = max(0, max_full - current_top)

        assigned_set_tokens = set()  # tokens to avoid reassigning already-assigned drones
        def _token(d): return id(d)

        # Assigned to top field (closest drones)
        if top_group_valid and need_top > 0:
            top_center_x = (top_field.left + top_field.right) / 2.0
            top_center_y = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for d in components:
                if _drone_state(d) == 'protecting' and _drone_target_field(d) == top_field.id:
                    continue
                loc = getattr(d, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0.0) - top_center_x
                    dy = getattr(loc, 'y', 0.0) - top_center_y
                    dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            to_assign = min(need_top, len(candidates))
            for i in range(to_assign):
                d = candidates[i][1]
                environment.assign_group(d, top_group)
                assigned_set_tokens.add(_token(d))

        # Also mark any drones currently protecting the top field as assigned to the top group
        for d in components:
            if _drone_state(d) == 'protecting' and _drone_target_field(d) == top_field.id:
                assigned_set_tokens.add(_token(d))

        # Remaining drones that are not assigned to top protection
        remaining = [d for d in components if _token(d) not in assigned_set_tokens]

        # Attempt to fully protect subsequent fields if possible
        for f in threatened[1:]:
            if getattr(f, 'threat_level', 0) <= 0:
                continue
            g_id = f"protecting {f.id}"
            if g_id not in group_ids:
                continue

            # Current protection for this field
            current = sum(1 for d in components if _drone_state(d) == 'protecting' and _drone_target_field(d) == f.id)
            needed = max(0, min(getattr(f, 'drones_for_full_protection', 0), len(remaining)) - current)
            if needed <= 0:
                continue

            center_x = (f.left + f.right) / 2.0
            center_y = (f.top + f.bottom) / 2.0

            rem_sorted = []
            for d in remaining:
                loc = getattr(d, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0.0) - center_x
                    dy = getattr(loc, 'y', 0.0) - center_y
                    dist = (dx*dx + dy*dy) ** 0.5
                rem_sorted.append((dist, d))
            rem_sorted.sort(key=lambda t: t[0])

            chosen = [cc for _, cc in rem_sorted[:needed]]
            for d in chosen:
                environment.assign_group(d, g_id)
            # Remove chosen from remaining
            remaining = [d for d in remaining if d not in chosen]

        # Finally, idle any drones not assigned to any protection group
        for d in components:
            # If a drone is currently protecting the top field, ensure it's in the correct group
            if _drone_state(d) == 'protecting' and _drone_target_field(d) == top_field.id:
                if top_group_valid:
                    environment.assign_group(d, top_group)
                else:
                    environment.assign_group(d, "idle")
            else:
                # If the drone is not already allocated to a protection group this step, idle it
                # We cannot reliably detect "previous" group state across steps here, so idle by default
                environment.assign_group(d, "idle")