from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: find fields with threat
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Step 2: choose the highest-threat field
        target_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        target_group = f"protecting {target_field.id}"

        # Step 3: current protectors for the target field
        currently_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_field.id
        ]
        currently_protecting_count = len(currently_protecting)
        needed = getattr(target_field, "drones_for_full_protection", 0)

        # If we can't define a meaningful need, keep current protectors and idle the rest
        if needed <= 0:
            for d in components:
                if d in currently_protecting:
                    environment.assign_group(d, target_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # If already fully protected, keep protectors and idle the rest
        if currently_protecting_count >= needed:
            for d in components:
                if d in currently_protecting:
                    environment.assign_group(d, target_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Step 4: compute how many more drones are needed
        remaining_needed = needed - currently_protecting_count

        # Field center
        cx = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        cy = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Step 5: gather candidate drones (not already protecting this field)
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_field.id:
                continue
            loc = getattr(d, "location", None)
            if loc is None:
                dist = float("inf")
            else:
                dx = getattr(loc, "x", 0)
                dy = getattr(loc, "y", 0)
                dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
            candidates.append((dist, d))

        candidates.sort(key=lambda t: t[0])

        # Step 6: pick the closest drones to fill the gap
        to_assign = [d for _, d in candidates[:max(0, remaining_needed)]]

        # Assign chosen drones to protect target field
        for d in to_assign:
            environment.assign_group(d, target_group)

        # Step 7: idle all remaining drones
        for d in components:
            if d in currently_protecting or d in to_assign:
                continue
            environment.assign_group(d, "idle")