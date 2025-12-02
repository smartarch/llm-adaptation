from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with non-zero threat
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helpers
        def center_of(field):
            left = getattr(field, "left", 0)
            top = getattr(field, "top", 0)
            right = getattr(field, "right", 0)
            bottom = getattr(field, "bottom", 0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        def current_protecting(field):
            fid = getattr(field, "id", None)
            return sum(1 for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid)

        allocated = set()
        assignments = {}

        def assign_to_field(drone, field):
            fid = getattr(field, "id", None)
            group = f"protecting {fid}"
            assignments[drone] = group
            allocated.add(drone)

        # Step 1: Primary field allocation
        primary = threat_fields[0]
        primary_id = getattr(primary, "id", None)
        primary_needed = max(0, int(getattr(primary, "drones_for_full_protection", 0)))
        primary_current = current_protecting(primary)

        cx, cy = center_of(primary)
        deficit = max(0, primary_needed - primary_current)

        # If we need to fill primary, pick closest drones not already protecting primary
        primary_candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                continue
            loc = getattr(d, "location", None)
            if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                dist = float("inf")
            else:
                dist = ((getattr(loc, "x") - cx) ** 2 + (getattr(loc, "y") - cy) ** 2) ** 0.5
            primary_candidates.append((dist, d))
        primary_candidates.sort(key=lambda t: t[0])
        for i in range(min(deficit, len(primary_candidates))):
            d = primary_candidates[i][1]
            assign_to_field(d, primary)

        # Step 2: Allocate to secondary fields in threat order
        for field in threat_fields[1:]:
            fid = getattr(field, "id", None)
            needed = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            current = current_protecting(field)
            deficit = max(0, needed - current)
            if deficit <= 0:
                continue

            cx, cy = center_of(field)
            candidates = []
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    continue
                loc = getattr(d, "location", None)
                if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                    dist = float("inf")
                else:
                    dist = ((getattr(loc, "x") - cx) ** 2 + (getattr(loc, "y") - cy) ** 2) ** 0.5
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            for i in range(min(deficit, len(candidates))):
                d = candidates[i][1]
                if d not in allocated:
                    assign_to_field(d, field)

        # Step 3: Any drones not allocated go idle
        for d in components:
            if d not in allocated:
                assignments[d] = "idle"

        # Apply final assignments
        for d, group in assignments.items():
            environment.assign_group(d, group)