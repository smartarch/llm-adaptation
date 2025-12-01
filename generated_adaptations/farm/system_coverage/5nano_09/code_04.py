from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with any threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low), tie-break by area (deterministic)
        def field_area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        fields_sorted = sorted(
            fields_with_threat,
            key=lambda f: (getattr(f, "threat_level", 0), field_area(f)),
            reverse=True
        )

        # Top field (highest threat)
        top_field = fields_sorted[0]
        # Current protectors for top field
        top_protectors = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id]
        current_top_protect = len(top_protectors)
        top_required = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        assignments = {}

        # Ensure existing top field protectors stay
        for c in top_protectors:
            assignments[c] = f"protecting {top_field.id}"

        # Center of top field
        top_cx = (top_field.left + top_field.right) / 2.0
        top_cy = (top_field.top + top_field.bottom) / 2.0

        # Drones pool that are not currently protecting the top field
        candidates_top = [c for c in components if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id)]

        if top_required > 0:
            cand_dist = []
            for c in candidates_top:
                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - top_cx
                    dy = getattr(loc, "y", 0.0) - top_cy
                    dist = (dx*dx + dy*dy) ** 0.5
                else:
                    dist = float("inf")
                cand_dist.append((dist, c))
            cand_dist.sort(key=lambda t: t[0])
            for i in range(min(top_required, len(cand_dist))):
                _, drone = cand_dist[i]
                assignments[drone] = f"protecting {top_field.id}"

        # Process remaining fields in threat order (excluding the top field)
        remaining_fields = fields_sorted[1:]
        top_set = set(top_protectors)

        for field in remaining_fields:
            current = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id)
            max_for_field = getattr(field, "drones_for_full_protection", 0)
            if current >= max_for_field:
                # Already fully protected; ensure its protectors stay
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                        assignments[c] = f"protecting {field.id}"
                continue

            needed = max(0, max_for_field - current)
            if needed <= 0:
                # Nothing to do for this field
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                        assignments[c] = f"protecting {field.id}"
                continue

            # Center of this field
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            # Candidate drones: avoid disrupting top field; avoid drones already protecting this field
            candidates = []
            for c in components:
                if c in top_set:
                    continue  # do not take drones away from top field
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                    continue  # already protecting this field
                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                else:
                    dist = float("inf")
                candidates.append((dist, c))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                _, drone = candidates[i]
                assignments[drone] = f"protecting {field.id}"

            # Ensure current protectors for this field stay
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                    assignments[c] = f"protecting {field.id}"

        # Apply assignments:
        for c in components:
            if c in assignments:
                environment.assign_group(c, assignments[c])
            else:
                # Derive current group from the drone's state/target
                state = getattr(c, "state", None)
                target = getattr(c, "target_id", None)
                if state == "protecting" and target is not None:
                    environment.assign_group(c, f"protecting {target}")
                elif state == "moving_to_field" and target is not None:
                    environment.assign_group(c, f"protecting {target}")
                else:
                    environment.assign_group(c, "idle")