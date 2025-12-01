from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with any threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If there is no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: field area (deterministic tie-breaker)
        def field_area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        # Sort fields by threat level (desc) then area (desc)
        fields_sorted = sorted(
            fields_with_threat,
            key=lambda f: (getattr(f, "threat_level", 0), field_area(f)),
            reverse=True
        )

        # Assignments to build: drone -> group string
        assignments = {}

        # Helper: gather current protectors for a given field, including already assigned ones
        def current_protectors_for(field_id):
            prot = set()
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id:
                    prot.add(c)
            # include those already assigned to this field in assignments
            for c, grp in assignments.items():
                if grp == f"protecting {field_id}":
                    prot.add(c)
            return prot

        # Track drones that have been assigned in this step (to avoid reusing them)
        assigned_in_step = set()

        # Process fields in threat order
        for field in fields_sorted:
            fid = field.id
            current = len(current_protectors_for(fid))
            required = max(0, getattr(field, "drones_for_full_protection", 0) - current)

            # If already fully protected, ensure its drones are assigned to this field
            if current >= getattr(field, "drones_for_full_protection", 0):
                for c in current_protectors_for(fid):
                    assignments[c] = f"protecting {fid}"
                    assigned_in_step.add(c)
                continue

            # If we need more drones, allocate from closest available drones
            if required > 0:
                # Center of the field
                cx = (field.left + field.right) / 2.0
                cy = (field.top + field.bottom) / 2.0

                # Candidates: drones not already assigned to any field and not currently protecting any field
                candidates = []
                for c in components:
                    if c in assigned_in_step:
                        continue
                    # Do not take drones already protecting any field (to avoid disrupting existing protection)
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                        continue
                    loc = getattr(c, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    else:
                        dist = float("inf")
                    candidates.append((dist, c))

                # Sort by distance (closest first)
                candidates.sort(key=lambda t: t[0])

                # Assign the closest drones to this field
                for i in range(min(required, len(candidates))):
                    _, drone = candidates[i]
                    assignments[drone] = f"protecting {fid}"
                    assigned_in_step.add(drone)

            # Ensure existing protectors for this field stay (in final assignments)
            for c in current_protectors_for(fid):
                assignments[c] = f"protecting {fid}"
                assigned_in_step.add(c)

        # Apply the final group assignments
        for c in components:
            group = assignments.get(c, "idle")
            environment.assign_group(c, group)