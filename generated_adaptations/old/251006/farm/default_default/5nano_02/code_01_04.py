from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with threat
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Target the field with highest threat
        target_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        target_group = f"protecting {target_field.id}"

        # Current protectors for the target field
        currently_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_field.id
        ]
        currently_protecting_set = set(currently_protecting)
        currently_protecting_count = len(currently_protecting)
        needed = getattr(target_field, "drones_for_full_protection", 0)

        # If can't define meaningful need or already fully protected
        if needed <= 0 or currently_protecting_count >= needed:
            for d in components:
                if d in currently_protecting_set:
                    environment.assign_group(d, target_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Compute remaining drones needed to reach full protection
        remaining_needed = needed - currently_protecting_count

        # Field center
        cx = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        cy = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Gather candidate drones not currently protecting this field
        candidates = []
        for d in components:
            if d in currently_protecting_set:
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

        # Choose the closest drones to fill the gap
        to_assign = [d for _, d in candidates[:max(0, remaining_needed)]]

        # Final assignment: protect chosen drones and idle the rest
        assigned_set = currently_protecting_set.union(to_assign)
        for d in components:
            if d in assigned_set:
                environment.assign_group(d, target_group)
            else:
                environment.assign_group(d, "idle")