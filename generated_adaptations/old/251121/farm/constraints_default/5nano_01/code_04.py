from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, send all drones to idle
        if not threatening_fields:
            for d in components:
                target = "idle" if "idle" in group_ids else group_ids[0]
                if target not in group_ids:
                    target = "idle"
                environment.assign_group(d, target)
            return

        # Choose the top-threat field
        top_field = max(threatening_fields, key=lambda f: getattr(f, "threat_level", 0))
        # Center of the field
        cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
        cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

        # Helper to determine a drone's current group
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                return f"protecting {d.target_id}"
            else:
                return "idle"

        top_group = f"protecting {top_field.id}"
        # Drones currently protecting the top field
        top_current = [d for d in components if current_group(d) == top_group]
        current_count = len(top_current)
        required = int(getattr(top_field, "drones_for_full_protection", 1))
        needed = max(0, required - current_count)

        # Determine which drones should be moved to top_field to fill deficiency
        to_move = set()
        if needed > 0:
            candidates = []
            for d in components:
                if current_group(d) == top_group:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dx = getattr(loc, "x", 0) - cx
                    dy = getattr(loc, "y", 0) - cy
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, d))
            candidates.sort(key=lambda t: t[0])
            for i in range(min(needed, len(candidates))):
                to_move.add(candidates[i][1])

        # Final assignment per drone: assign to their target group
        for d in components:
            if d in to_move or current_group(d) == top_group:
                target_group = top_group
            else:
                target_group = current_group(d)

            # Fallback to a valid group if necessary
            if target_group not in group_ids:
                target_group = "idle" if "idle" in group_ids else group_ids[0]

            environment.assign_group(d, target_group)