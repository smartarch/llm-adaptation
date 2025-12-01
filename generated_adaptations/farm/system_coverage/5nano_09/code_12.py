from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with any threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: deterministic field area
        def field_area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        # Sort fields by threat level (desc) then area (desc)
        fields_sorted = sorted(
            fields_with_threat,
            key=lambda f: (getattr(f, "threat_level", 0), field_area(f)),
            reverse=True
        )

        # Build rank map for fields
        rank = {f.id: i for i, f in enumerate(fields_sorted)}

        assignments = {}
        assigned_in_step = set()

        # Process fields in threat order
        for field in fields_sorted:
            fid = field.id
            # Count current protectors for this field (including those already assigned in this step)
            current = 0
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                    current += 1
            for c, grp in assignments.items():
                if grp == f"protecting {fid}":
                    current += 1

            # If already fully protected, ensure protectors stay
            if current >= getattr(field, "drones_for_full_protection", 0):
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                        assignments[c] = f"protecting {fid}"
                        assigned_in_step.add(c)
                continue

            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                        assignments[c] = f"protecting {fid}"
                        assigned_in_step.add(c)
                continue

            # Center of the field
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            # Build movable candidates: idle, moving_to_field, or protecting a lower-priority field
            candidates = []
            for c in components:
                if c in assigned_in_step:
                    continue

                state = getattr(c, "state", None)
                movable = False
                if state in ("idle", "moving_to_field"):
                    movable = True
                elif state == "protecting":
                    t = getattr(c, "target_id", None)
                    if t is None:
                        movable = True
                    else:
                        if rank.get(t, 999) > rank[fid]:
                            movable = True
                if not movable:
                    continue

                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = (dx * dx + dy * dy) ** 0.5
                else:
                    dist = float("inf")

                candidates.append((dist, c))

            candidates.sort(key=lambda t: t[0])
            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                assignments[drone] = f"protecting {fid}"
                assigned_in_step.add(drone)

            # Ensure current protectors stay
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                    assignments[c] = f"protecting {fid}"
                    assigned_in_step.add(c)

        # Apply final groups
        for c in components:
            if c in assignments:
                environment.assign_group(c, assignments[c])
            else:
                # Fallback: preserve current protection if any, else idle
                st = getattr(c, "state", None)
                t = getattr(c, "target_id", None)
                if st == "protecting" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                elif st == "moving_to_field" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                else:
                    environment.assign_group(c, "idle")