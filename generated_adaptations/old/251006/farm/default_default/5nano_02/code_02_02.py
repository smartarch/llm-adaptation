from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Target the field with the highest threat
        target_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))
        target_group = f"protecting {target_field.id}"

        # Validate the group name exists
        if target_group not in group_ids:
            # Fallback: idle all to avoid invalid group usage
            for d in components:
                environment.assign_group(d, "idle")
            return

        needed = getattr(target_field, "drones_for_full_protection", 0)

        # Drones currently protecting the target field
        currently_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_field.id
        ]
        currently_protecting_set = set(currently_protecting)

        final_protectors = set()

        # If no meaningful protection needed yet
        if needed <= 0:
            final_protectors = currently_protecting_set
        # If already fully protected, keep current protectors
        elif len(currently_protecting) >= needed:
            final_protectors = currently_protecting_set
        else:
            # Need additional drones: pick the closest available to the field center
            remaining_needed = int(needed - len(currently_protecting))

            cx = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
            cy = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

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
            chosen = [d for _, d in candidates[:max(0, remaining_needed)]]
            final_protectors = currently_protecting_set.union(set(chosen))

        # Assign exactly one group per drone: either the protection group or idle
        for d in components:
            if d in final_protectors:
                environment.assign_group(d, target_group)
            else:
                environment.assign_group(d, "idle")