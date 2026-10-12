from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with any threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Deterministic area helper
        def area(f):
            return (getattr(f, "right") - getattr(f, "left")) * (getattr(f, "bottom") - getattr(f, "top"))

        # Sort fields by threat desc, then area desc
        fields_sorted = sorted(
            fields,
            key=lambda f: (getattr(f, "threat_level", 0), area(f)),
            reverse=True
        )

        # Field lookup for getting drones_for_full_protection easily
        field_by_id = {f.id: f for f in environment.fields}

        # Initial counts: how many drones protect each field in the current state
        current_by_field = {}
        for f in environment.fields:
            if getattr(f, "threat_level", 0) > 0:
                fid = f.id
                current_by_field[fid] = 0

        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None and tid in current_by_field:
                    current_by_field[tid] = current_by_field.get(tid, 0) + 1

        assignments = {}
        assigned_in_step = set()
        assigned_counts = {fid: 0 for fid in current_by_field.keys()}

        # Helper: current protectors for a field including assignments in this step
        def current_for(fid):
            curr = current_by_field.get(fid, 0)
            curr += assigned_counts.get(fid, 0)
            return curr

        # Process fields in threat order
        for field in fields_sorted:
            fid = field.id
            # How many protectors do we currently have for this field (including this step)
            current = current_for(fid)
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current)

            # If already fully protected, ensure protectors stay
            if current >= getattr(field, "drones_for_full_protection", 0):
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        if d not in assignments:
                            assignments[d] = f"protecting {fid}"
                            assigned_in_step.add(d)
                            assigned_counts[fid] = assigned_counts.get(fid, 0) + 1
                continue

            if needed <= 0:
                # Nothing to allocate, but ensure existing protectors stay
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        if d not in assignments:
                            assignments[d] = f"protecting {fid}"
                            assigned_in_step.add(d)
                            assigned_counts[fid] = assigned_counts.get(fid, 0) + 1
                continue

            # Field center
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            # Build candidate pool:
            candidates = []

            # 1) Extras: drones currently protecting a field with surplus beyond its own need
            for d in components:
                if d in assigned_in_step:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                    t = d.target_id
                    other = field_by_id.get(t)
                    if other is not None:
                        other_need = getattr(other, "drones_for_full_protection", 0)
                        other_cur = current_by_field.get(t, 0)
                        if other_cur > other_need:
                            # This drone can be moved
                            loc = getattr(d, "location", None)
                            if loc is not None:
                                dx = getattr(loc, "x", 0.0) - cx
                                dy = getattr(loc, "y", 0.0) - cy
                                dist = (dx*dx + dy*dy) ** 0.5
                            else:
                                dist = float("inf")
                            candidates.append((dist, d, t))

            # 2) Idle or moving drones
            for d in components:
                if d in assigned_in_step:
                    continue
                state = getattr(d, "state", None)
                if state in ("idle", "moving_to_field"):
                    loc = getattr(d, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    else:
                        dist = float("inf")
                    candidates.append((dist, d, None))

            # Sort by distance and allocate needed drones
            candidates.sort(key=lambda t: t[0])

            allocated = 0
            for dist, drone, src_field in candidates:
                if allocated >= needed:
                    break
                assignments[drone] = f"protecting {fid}"
                assigned_in_step.add(drone)
                allocated += 1
                assigned_counts[fid] = assigned_counts.get(fid, 0) + 1
                # No need to update current_by_field here; we rely on assigned_counts for current

            # Ensure current protectors for this field stay
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    if d not in assignments:
                        assignments[d] = f"protecting {fid}"
                        assigned_in_step.add(d)
                        assigned_counts[fid] = assigned_counts.get(fid, 0) + 1

        # Apply final assignments
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