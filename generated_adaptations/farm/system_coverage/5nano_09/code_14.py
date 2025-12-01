from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Deterministic area helper
        def area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        # Sort fields by threat (desc) then area (desc)
        fields_sorted = sorted(fields, key=lambda f: (getattr(f, "threat_level", 0), area(f)), reverse=True)

        # Helpers
        field_by_id = {f.id: f for f in environment.fields}
        idx_by_id = {f.id: i for i, f in enumerate(fields_sorted)}

        # Assignments and tracking
        assignments = {}
        assigned_in_step = set()

        # Helper to count current protectors for a field (including those assigned in this step)
        def current_count(field_id):
            cnt = 0
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                    cnt += 1
            for d, grp in assignments.items():
                if grp == f"protecting {field_id}":
                    cnt += 1
            return cnt

        # Process fields in threat order
        for field in fields_sorted:
            fid = field.id
            current = current_count(fid)
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current)

            # If already fully protected, lock protectors
            if current >= getattr(field, "drones_for_full_protection", 0):
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        assignments[d] = f"protecting {fid}"
                        assigned_in_step.add(d)
                continue

            if needed > 0:
                # Center of the field
                cx = (field.left + field.right) / 2.0
                cy = (field.top + field.bottom) / 2.0

                # Build movable candidates
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
                            # Allow moving from a lower-priority field
                            if idx_by_id.get(t, 999) > idx_by_id.get(fid, 0):
                                movable = True
                            else:
                                # Allow moving if that field has excess protections
                                other = field_by_id.get(t)
                                if other is not None:
                                    other_full = getattr(other, "drones_for_full_protection", 0)
                                    other_cur = current_count(t)
                                    if other_cur > other_full:
                                        movable = True
                    if not movable:
                        continue

                    loc = getattr(c, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    else:
                        dist = float("inf")

                    candidates.append((dist, c))

                candidates.sort(key=lambda t: t[0])

                # Assign the closest candidates to this field
                for i in range(min(needed, len(candidates))):
                    drone = candidates[i][1]
                    assignments[drone] = f"protecting {fid}"
                    assigned_in_step.add(drone)

            # Ensure current protectors for this field stay
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    assignments[d] = f"protecting {fid}"
                    assigned_in_step.add(d)

        # Apply final groups
        for c in components:
            if c in assignments:
                environment.assign_group(c, assignments[c])
            else:
                # Fallback: preserve current valid protection or idle
                st = getattr(c, "state", None)
                t = getattr(c, "target_id", None)
                if st == "protecting" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                elif st == "moving_to_field" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                else:
                    environment.assign_group(c, "idle")