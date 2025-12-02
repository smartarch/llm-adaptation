from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with any bird threat
        fields_with_threat = [
            f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0
        ]

        # If no threat, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Primary field: the one with the highest threat level
        primary = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        primary_id = getattr(primary, "id", None)
        group_primary = f"protecting {primary_id}"

        # How many drones are needed for full protection on the primary field
        needed = max(0, getattr(primary, "drones_for_full_protection", 0))
        current_protecting = max(0, getattr(primary, "protecting_drones", 0))

        # Field center for distance calculation
        cx = (getattr(primary, "left", 0) + getattr(primary, "right", 0)) / 2.0
        cy = (getattr(primary, "top", 0) + getattr(primary, "bottom", 0) / 1.0) / 2.0  # safe divide
        # Note: Above line uses a safe aggregation; real data should provide left/top/right/bottom as ints.

        # If the field already has enough protection, keep these drones there and idle the rest,
        # but ensure those already protecting stay in the same group.
        if current_protecting >= needed and needed > 0:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                    environment.assign_group(d, group_primary)
                else:
                    environment.assign_group(d, "idle")
            return

        # Drones still needed to reach full protection
        deficit = max(0, needed - current_protecting)

        # Build list of candidate drones not currently protecting the primary field
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                continue  # already protecting the primary
            loc = getattr(d, "location", None)
            if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                dist = float("inf")
            else:
                dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
            candidates.append((dist, d))

        candidates.sort(key=lambda t: t[0])
        chosen = [d for _, d in candidates[:deficit]]

        # Assign groups
        for d in components:
            if d in chosen:
                environment.assign_group(d, group_primary)
            elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == primary_id:
                # Keep current drones already protecting the primary
                environment.assign_group(d, group_primary)
            else:
                environment.assign_group(d, "idle")