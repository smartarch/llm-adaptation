from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with non-zero threat
        fields = getattr(environment, "fields", []) or []
        field_by_id = {getattr(f, "id", None): f for f in fields}
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        def center_of(field):
            left = getattr(field, "left", 0)
            top = getattr(field, "top", 0)
            right = getattr(field, "right", 0)
            bottom = getattr(field, "bottom", 0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        def count_protecting(field):
            fid = getattr(field, "id", None)
            return sum(1 for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid)

        allocated = set()
        # Helper to assign a drone to a field
        def assign_to_field(d, field):
            fid = getattr(field, "id", None)
            grp = f"protecting {fid}"
            environment.assign_group(d, grp)
            allocated.add(d)

        # Step 1: Primary field allocation (highest threat)
        primary = threat_fields[0]
        primary_id = getattr(primary, "id", None)
        primary_needed = max(0, int(getattr(primary, "drones_for_full_protection", 0)))
        primary_current = count_protecting(primary)

        # If primary is already fully protected, lock its drones and idle others
        if primary_needed > 0 and primary_current >= primary_needed:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                    environment.assign_group(d, f"protecting {primary_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        cx, cy = center_of(primary)
        deficit = max(0, primary_needed - primary_current)

        # Build candidate drones to defend primary (preferring those not currently protecting higher-threat fields)
        primary_candidates = []
        primary_threat = getattr(primary, "threat_level", 0)
        for d in components:
            # Skip drones already protecting primary
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                continue
            # If drone is protecting another field with threat >= primary, avoid taking it away
            if getattr(d, "state", None) == "protecting":
                other_id = getattr(d, "target_id", None)
                other_field = field_by_id.get(other_id)
                other_threat = getattr(other_field, "threat_level", 0) if other_field else 0
                if other_threat >= primary_threat:
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

        # Step 2: Allocate to secondary threat fields (in order) with remaining drones
        allocated_ids = set(allocated)
        for field in threat_fields[1:]:
            fid = getattr(field, "id", None)
            needed = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            current = count_protecting(field)
            deficit = max(0, needed - current)
            if deficit <= 0:
                # Ensure existing protectors stay assigned
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, f"protecting {fid}")
                continue

            cx, cy = center_of(field)
            candidates = []
            for d in components:
                if d in allocated_ids:
                    continue
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
                environment.assign_group(d, f"protecting {fid}")
                allocated_ids.add(d)

        # Step 3: Any drones not allocated go idle
        for d in components:
            if d not in allocated and d not in allocated_ids:
                environment.assign_group(d, "idle")