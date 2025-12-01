from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with threat > 0
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, put all drones to idle
        if not fields_with_threat:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Select the top field by threat level (deterministic tie-breaker by id)
        top_field = max(fields_with_threat, key=lambda f: (f.threat_level, str(getattr(f, "id", ""))))

        # Determine protection requirements
        required = int(getattr(top_field, "drones_for_full_protection", 0))
        if required <= 0:
            # No protection required for this field; idle all drones
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Compute the center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Drones currently protecting the top field
        currently_protecting = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id]

        # Always assign currently protecting drones to the correct group (explicit re-assign)
        for d in currently_protecting:
            environment.assign_group(d, f"protecting {top_field.id}")

        # If we already have enough drones protecting the top field, idle the rest
        if len(currently_protecting) >= required:
            for d in components:
                if d not in currently_protecting:
                    environment.assign_group(d, "idle")
            return

        # Need additional drones to reach the required count
        needed = required - len(currently_protecting)

        # Candidates are drones not already protecting top field; compute distance to field center
        candidates = []
        for d in components:
            if d in currently_protecting:
                continue
            loc = getattr(d, "location", None)
            dx = (loc.x if loc is not None else 0.0) - cx
            dy = (loc.y if loc is not None else 0.0) - cy
            dist2 = dx*dx + dy*dy
            candidates.append((dist2, d))

        candidates.sort(key=lambda t: t[0])

        # Assign the closest drones to protection group
        assigned_to_top = set(currently_protecting)
        count = 0
        for _, d in candidates:
            if count >= needed:
                break
            environment.assign_group(d, f"protecting {top_field.id}")
            assigned_to_top.add(d)
            count += 1

        # Any remaining drones go idle
        for d in components:
            if d not in assigned_to_top:
                environment.assign_group(d, "idle")