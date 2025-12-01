from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with any threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the top field by highest threat level (tie-break with area deterministically)
        def field_key(f):
            area = (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))
            return (getattr(f, "threat_level", 0), area)

        top_field = max(fields_with_threat, key=field_key)

        # Compute center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Current number of drones protecting the top field
        current_top_protect = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                current_top_protect += 1

        # Drones required for full protection
        required = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        # Prepare assignments
        assignments = {}

        # Keep already protecting drones on the top field
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                assignments[c] = f"protecting {top_field.id}"

        if required <= 0:
            # Top field already fully protected; idle all others
            for c in components:
                if c not in assignments:
                    assignments[c] = "idle"
        else:
            # Gather candidate drones (all except those already protecting top field)
            candidates = []
            for c in components:
                if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id):
                    loc = getattr(c, "location", None)
                    if loc is not None:
                        x = getattr(loc, "x", 0.0)
                        y = getattr(loc, "y", 0.0)
                        dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    else:
                        dist = float("inf")
                    candidates.append((dist, c))

            # Sort by distance (closest first)
            candidates.sort(key=lambda t: t[0])

            # Reassign the closest drones to top_field until we reach the required number
            for i in range(min(required, len(candidates))):
                _, drone = candidates[i]
                assignments[drone] = f"protecting {top_field.id}"

            # Remaining drones (not assigned yet) go idle
            for c in components:
                if c not in assignments:
                    assignments[c] = "idle"

        # Apply the assignments
        for c in components:
            env_group = assignments.get(c, "idle")
            environment.assign_group(c, env_group)