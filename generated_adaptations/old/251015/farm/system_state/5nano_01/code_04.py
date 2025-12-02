from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threat fields (threat_level > 0)
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If there are no threatened fields, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level descending
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: getattr(f, 'threat_level', 0.0),
            reverse=True
        )

        plan = {}  # drone -> group_id
        used = set()

        # Step 1: Top field protection
        top_field = threat_fields_sorted[0]
        top_id = top_field.id

        # Drones already protecting the top field (continuity)
        keepers_top = [
            d for d in components
            if getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) == top_id
        ]
        for d in keepers_top:
            plan[d] = f"protecting {top_id}"
            used.add(d)

        # How many more drones are needed for full protection of top field
        required_top = int(getattr(top_field, 'drones_for_full_protection', 0))
        extras_needed = max(0, required_top - len(keepers_top))

        if extras_needed > 0:
            # Compute top field center
            left = getattr(top_field, 'left', 0.0)
            right = getattr(top_field, 'right', 0.0)
            top = getattr(top_field, 'top', 0.0)
            bottom = getattr(top_field, 'bottom', 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            # Candidates are drones not already kept for the top field
            candidates = [d for d in components if d not in keepers_top]

            dist_pairs = []
            for d in candidates:
                loc = getattr(d, 'location', None)
                if loc is None:
                    dx = dy = 0.0
                else:
                    dx = getattr(loc, 'x', 0.0) - cx
                    dy = getattr(loc, 'y', 0.0) - cy
                dist2 = dx*dx + dy*dy
                dist_pairs.append((dist2, d))

            dist_pairs.sort(key=lambda t: t[0])

            for _, d in dist_pairs[:extras_needed]:
                plan[d] = f"protecting {top_id}"
                used.add(d)

        # Step 2: Other threat fields (in descending threat order)
        for field in threat_fields_sorted[1:]:
            fid = field.id

            # Continuity: keep current protectors for this field if any
            keepers = [
                d for d in components
                if getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) == fid
            ]
            for d in keepers:
                if d not in plan:
                    plan[d] = f"protecting {fid}"
                    used.add(d)

            # Drones needed to fully protect this field
            required = int(getattr(field, 'drones_for_full_protection', 0))
            extras_needed = max(0, required - len(keepers))

            if extras_needed <= 0:
                continue

            # Choose closest drones not already planned
            left = getattr(field, 'left', 0.0)
            right = getattr(field, 'right', 0.0)
            top = getattr(field, 'top', 0.0)
            bottom = getattr(field, 'bottom', 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            candidates = [d for d in components if d not in plan]
            dist_pairs = []
            for d in candidates:
                loc = getattr(d, 'location', None)
                if loc is None:
                    dx = dy = 0.0
                else:
                    dx = getattr(loc, 'x', 0.0) - cx
                    dy = getattr(loc, 'y', 0.0) - cy
                dist2 = dx*dx + dy*dy
                dist_pairs.append((dist2, d))
            dist_pairs.sort(key=lambda t: t[0])

            for _, d in dist_pairs[:extras_needed]:
                plan[d] = f"protecting {fid}"
                used.add(d)

        # Step 3: Remaining drones go idle
        for d in components:
            if d not in plan:
                plan[d] = "idle"

        # Apply the plan
        for d in components:
            environment.assign_group(d, plan[d])