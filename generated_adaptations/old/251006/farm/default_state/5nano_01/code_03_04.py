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
            final_group = {d: "idle" for d in components}
            for d, grp in final_group.items():
                environment.assign_group(d, grp)
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        def center_of(field):
            left = getattr(field, "left", 0)
            top = getattr(field, "top", 0)
            right = getattr(field, "right", 0)
            bottom = getattr(field, "bottom", 0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        # Helper to count drones currently protecting a field, excluding ones already allocated
        allocated = set()
        final_group = {}

        def assign_to(d, gid):
            final_group[d] = gid
            allocated.add(d)

        def count_protecting(field):
            fid = getattr(field, "id", None)
            count = 0
            for d in components:
                if d in allocated:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    count += 1
            return count

        # Step 1: Primary field allocation (highest threat)
        primary = threat_fields[0]
        primary_id = getattr(primary, "id", None)
        primary_needed = max(0, int(getattr(primary, "drones_for_full_protection", 0)))
        primary_current = count_protecting(primary)

        # If primary is already fully protected, lock its drones and idle others
        if primary_needed > 0 and primary_current >= primary_needed:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                    assign_to(d, f"protecting {primary_id}")
                else:
                    assign_to(d, "idle")
            # Apply final assignments
            for d, grp in final_group.items():
                environment.assign_group(d, grp)
            return

        cx, cy = center_of(primary)
        deficit = max(0, primary_needed - primary_current)

        # Build candidate drones to defend primary (prefer idle or not currently protecting primary)
        candidates = []
        for d in components:
            if d in allocated:
                continue
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                continue
            # distance to primary center
            loc = getattr(d, "location", None)
            if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                dist = float("inf")
            else:
                dist = ((getattr(loc, "x") - cx) ** 2 + (getattr(loc, "y") - cy) ** 2) ** 0.5
            candidates.append((dist, d))
        candidates.sort(key=lambda t: t[0])

        for i in range(min(deficit, len(candidates))):
            d = candidates[i][1]
            assign_to(d, f"protecting {primary_id}")

        # Step 2: Allocate to secondary threat fields (in order) with remaining drones
        for field in threat_fields[1:]:
            fid = getattr(field, "id", None)
            needed = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            current = count_protecting(field)
            deficit = max(0, needed - current)
            if deficit <= 0:
                continue

            cx, cy = center_of(field)
            candidates = []
            for d in components:
                if d in allocated:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    # already allocated to this field
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
                assign_to(d, f"protecting {fid}")

        # Step 3: Any drones not allocated go idle
        for d in components:
            if d not in allocated:
                assign_to(d, "idle")

        # Apply final assignments
        for d, grp in final_group.items():
            environment.assign_group(d, grp)