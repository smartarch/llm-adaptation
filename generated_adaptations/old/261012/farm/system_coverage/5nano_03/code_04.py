from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat fields: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level descending
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers
        field_centers = {}
        for f in threat_fields:
            field_centers[f.id] = (
                (f.left + f.right) / 2.0,
                (f.top + f.bottom) / 2.0
            )

        assigned_ids = set()

        # Process fields in order of decreasing threat
        for field in threat_fields:
            top_group = f"protecting {field.id}"
            # Current protectors for this field
            current_protectors = [
                c for c in components
                if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == field.id
            ]
            current_count = len(current_protectors)

            # If enough drones are already protecting this field, ensure they're in the correct group
            if current_count >= getattr(field, "drones_for_full_protection", 0):
                for c in current_protectors:
                    environment.assign_group(c, top_group)
                    assigned_ids.add(id(c))
                continue

            # Ensure current protectors stay with this field
            for c in current_protectors:
                environment.assign_group(c, top_group)
                assigned_ids.add(id(c))

            # Determine how many more drones are needed for full protection
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current_count)

            if needed > 0:
                cx, cy = field_centers[field.id]
                # Build candidate pool: drones not yet assigned
                candidates = []
                for c in components:
                    if id(c) in assigned_ids:
                        continue
                    loc = getattr(c, "location", None)
                    dist = float("inf")
                    if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                        dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
                    candidates.append((dist, c))
                candidates.sort(key=lambda t: t[0])

                # Assign the closest drones to this field up to the needed amount
                for i in range(min(needed, len(candidates))):
                    _, drone = candidates[i]
                    environment.assign_group(drone, top_group)
                    assigned_ids.add(id(drone))

        # Any drones not assigned to a protecting group become idle
        for c in components:
            if id(c) not in assigned_ids:
                environment.assign_group(c, "idle")