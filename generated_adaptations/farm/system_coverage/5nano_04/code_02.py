from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: determine top threat field
        fields = list(environment.fields)
        fields_with_threat = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            # No field needs protection: park all drones idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat_level
        top_field = max(fields_with_threat, key=lambda f: f.threat_level)

        # Compute the center of the field for distance calculations
        left, right = top_field.left, top_field.right
        top, bottom = top_field.top, top_field.bottom
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Step 2: current protection count for the top field
        n_current = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                n_current += 1

        # Step 3: required drones for full protection
        required = getattr(top_field, "drones_for_full_protection", 0)
        if required <= 0:
            # If for some reason the field doesn't require drones, set all idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        # If already fully protected, keep them there; others idle.
        if n_current >= required:
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                    environment.assign_group(c, f"protecting {top_field.id}")
                else:
                    environment.assign_group(c, "idle")
            return

        # Step 4: need to reallocate (required - n_current) drones to top_field
        to_allocate = required - n_current

        # Build candidate drones: those not currently protecting top_field
        candidates = []
        for c in components:
            if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id):
                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - center_x
                    dy = getattr(loc, "y", 0.0) - center_y
                    dist2 = dx*dx + dy*dy
                    candidates.append((dist2, c))
                else:
                    # If no location info, place them far away in distance metric
                    candidates.append((float('inf'), c))

        # Sort candidates by distance (closest first)
        candidates.sort(key=lambda t: t[0])

        allocated = set()
        for i in range(min(to_allocate, len(candidates))):
            _, c = candidates[i]
            environment.assign_group(c, f"protecting {top_field.id}")
            allocated.add(c)

        # Step 5: assign everyone else to idle (including those not allocated)
        for c in components:
            if c in allocated:
                # already assigned to top_field
                continue
            if (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id):
                # This would be unexpected (should have been counted in n_current or allocated),
                # but ensure it remains in the correct group
                environment.assign_group(c, f"protecting {top_field.id}")
            else:
                environment.assign_group(c, "idle")