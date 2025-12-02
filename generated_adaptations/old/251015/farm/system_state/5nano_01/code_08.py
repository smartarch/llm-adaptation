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
        # Track drones already planned to avoid duplicates
        planned = set()

        # Helper to collect inbound/protecting drones for a field
        def field_protectors(field):
            fid = field.id
            protectors = [
                d for d in components
                if getattr(d, 'target_id', None) == fid and getattr(d, 'state', '') in ('protecting', 'moving_to_field')
            ]
            return protectors

        # Step 1: Top field protection
        top_field = threat_fields_sorted[0]
        top_id = top_field.id
        keepers_top = field_protectors(top_field)

        for d in keepers_top:
            plan[d] = f"protecting {top_id}"
            planned.add(d)

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

            # Candidates are drones not already kept or planned for top
            candidates = [d for d in components if d not in planned]

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
                planned.add(d)

        # Step 2: Remaining threat fields (in descending threat order)
        for field in threat_fields_sorted[1:]:
            fid = field.id
            protectors = field_protectors(field)

            for d in protectors:
                if d not in planned:
                    plan[d] = f"protecting {fid}"
                    planned.add(d)

            required = int(getattr(field, 'drones_for_full_protection', 0))
            extras_needed = max(0, required - len(protectors))

            if extras_needed <= 0:
                continue

            # Compute field center
            left = getattr(field, 'left', 0.0)
            right = getattr(field, 'right', 0.0)
            top = getattr(field, 'top', 0.0)
            bottom = getattr(field, 'bottom', 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            candidates = [d for d in components if d not in planned]
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
                planned.add(d)

        # Step 3: Remaining drones go idle
        for d in components:
            if d not in plan:
                plan[d] = "idle"

        # Apply the plan
        for d in components:
            environment.assign_group(d, plan[d])