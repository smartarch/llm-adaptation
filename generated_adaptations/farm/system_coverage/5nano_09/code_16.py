from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Deterministic area helper
        def area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        # Sort fields by threat primarily, then area (desc)
        fields_sorted = sorted(
            fields,
            key=lambda f: (getattr(f, "threat_level", 0), area(f)),
            reverse=True
        )
        # Rank map for priority
        rank = {f.id: i for i, f in enumerate(fields_sorted)}
        field_by_id = {f.id: f for f in environment.fields}
        # Helper to center
        def center_of(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Helper: current protectors for a field, including those assigned in this step
        def current_count_with_assign(field_id, assignments):
            cnt = 0
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                    cnt += 1
            for d, grp in assignments.items():
                if grp == f"protecting {field_id}":
                    cnt += 1
            return cnt

        assignments = {}
        assigned_in_step = set()

        # Process fields in threat order
        for field in fields_sorted:
            fid = field.id
            current = current_count_with_assign(fid, assignments)
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                # Ensure currently protecting drones stay on this field
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        assignments[d] = f"protecting {fid}"
                        assigned_in_step.add(d)
                continue

            cx, cy = center_of(field)
            # We'll allocate up to 'needed' drones using a look-ahead scoring
            for _ in range(min(needed, len(components))):
                best_drone = None
                best_score = -1e9

                # Evaluate all movable candidates
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
                            # Allow moving from lower-priority field
                            if rank.get(t, 999) > rank.get(fid, 0):
                                movable = True
                            else:
                                # Allow moving from a field with extras beyond its own need
                                other = field_by_id.get(t)
                                cur_t = current_count_with_assign(t, assignments)
                                if other is not None and cur_t > getattr(other, "drones_for_full_protection", 0):
                                    movable = True
                    if not movable:
                        continue

                    loc = getattr(c, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = math.hypot(dx, dy)
                    else:
                        dist = float("inf")

                    # Score: high weight if this move would finish the field
                    new_current = current + 1
                    ri = getattr(field, "drones_for_full_protection", 0)
                    would_finish = 1 if (current < ri <= new_current) else 0
                    score = (-dist) + (10000 * would_finish)

                    if score > best_score:
                        best_score = score
                        best_drone = c

                if best_drone is None:
                    break
                # Assign best drone to this field
                assignments[best_drone] = f"protecting {fid}"
                assigned_in_step.add(best_drone)
                current += 1

            # Ensure existing protectors stay
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    assignments[d] = f"protecting {fid}"
                    assigned_in_step.add(d)

        # Apply final groups
        for c in components:
            if c in assignments:
                environment.assign_group(c, assignments[c])
            else:
                # Fallback: preserve current protection or idle
                st = getattr(c, "state", None)
                t = getattr(c, "target_id", None)
                if st == "protecting" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                elif st == "moving_to_field" and t is not None:
                    environment.assign_group(c, f"protecting {t}")
                else:
                    environment.assign_group(c, "idle")