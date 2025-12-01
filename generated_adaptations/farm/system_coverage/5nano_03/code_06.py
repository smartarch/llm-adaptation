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

        # Process fields in descending threat order
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers
        field_centers = {}
        for f in threat_fields:
            field_centers[f.id] = (
                (f.left + f.right) / 2.0,
                (f.top + f.bottom) / 2.0
            )

        # Final mapping: component -> group_id
        final_group_for = {}
        assigned = set()  # set of id(component) that have been assigned

        for field in threat_fields:
            top_group = f"protecting {field.id}"
            center = field_centers[field.id]
            # Current protectors for this field (we will cap to drones_for_full_protection)
            current_protectors = [
                c for c in components
                if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == field.id
            ]
            max_protect = int(getattr(field, "drones_for_full_protection", 0))

            # Keep up to max_protect protectors for this field
            keepers = current_protectors[:max_protect]
            for c in keepers:
                final_group_for[c] = top_group
                assigned.add(id(c))

            # If we need more to reach full protection, assign closest available drones
            needed = max(0, max_protect - len(keepers))
            if needed > 0:
                # Build candidates not yet assigned
                candidates = []
                for c in components:
                    if id(c) in assigned:
                        continue
                    loc = getattr(c, "location", None)
                    dist = float("inf")
                    if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                        dist = ((loc.x - center[0]) ** 2 + (loc.y - center[1]) ** 2) ** 0.5
                    candidates.append((dist, c))
                candidates.sort(key=lambda t: t[0])

                for i in range(min(needed, len(candidates))):
                    drone = candidates[i][1]
                    final_group_for[drone] = top_group
                    assigned.add(id(drone))

        # Any drones not assigned yet should be idle
        for c in components:
            if id(c) not in assigned:
                final_group_for[c] = "idle"

        # Apply assignments (exactly once per drone)
        for c in components:
            environment.assign_group(c, final_group_for[c])