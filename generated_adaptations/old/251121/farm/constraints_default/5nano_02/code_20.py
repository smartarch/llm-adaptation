from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        group_set = set(group_ids)

        # 1) Identify the field with the highest threat
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            thr = getattr(f, "threat_level", 0.0)
            if thr > max_threat:
                max_threat = thr
                top_field = f
            elif thr == max_threat and top_field is not None:
                if getattr(f, "id", "") < getattr(top_field, "id", ""):
                    top_field = f

        # If there is no threat, idle all (or fallback)
        if top_field is None or getattr(top_field, "threat_level", 0.0) <= 0.0:
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        group_top = f"protecting {top_field.id}"
        if group_top not in group_set:
            # If we cannot assign to the top-field group, idle all (fallback)
            if "idle" in group_set:
                for d in components:
                    environment.assign_group(d, "idle")
            else:
                fallback_group = next(iter(group_set), None)
                for d in components:
                    if fallback_group is not None:
                        environment.assign_group(d, fallback_group)
            return

        # 2) How many drones are needed for full protection of the top field?
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # 3) Current protection of the top field
        current_top = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_top += 1

        needed_top = max(0, required_top - current_top)

        # 4) Build explicit assignment map (drone -> group)
        assigned = {}

        # 4a) Continuity: keep drones already protecting the top field
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                assigned[d] = group_top

        # 4b) If more are needed for top field, pick closest drones
        if needed_top > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for d in components:
                if d in assigned:
                    continue
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                # Prefer idle drones first (to minimize disruption), then others
                is_idle = getattr(d, "state", "") == "idle"
                candidates.append((0 if is_idle else 1, dist2, getattr(d, "id", ""), d))
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            for i in range(min(needed_top, len(candidates))):
                _, _, _, d = candidates[i]
                assigned[d] = group_top

        # 4c) Distribute remaining idle/moving_to_field drones to other fields up to half protection
        total_drones = len(components)
        target_half = (total_drones + 1) // 2

        current_total_protecting = sum(1 for d in components if getattr(d, "state", None) == "protecting")

        if current_total_protecting < target_half:
            # Order other threatened fields by threat
            threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0 and getattr(f, "id", None) != getattr(top_field, "id", None)]
            threatened.sort(key=lambda ff: getattr(ff, "threat_level", 0.0), reverse=True)

            for f in threatened:
                gid = f"protecting {f.id}"
                if gid not in group_set:
                    continue

                # current on this field
                current_field = sum(1 for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id)
                needed_field = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_field)
                if needed_field <= 0:
                    continue

                cx = (f.left + f.right) / 2.0
                cy = (f.top + f.bottom) / 2.0

                # pool: drones not currently protecting any field (prefer idle then moving_to_field)
                pool = []
                for d in components:
                    if d in assigned:
                        continue
                    st = getattr(d, "state", "")
                    if st == "protecting":
                        continue
                    loc = getattr(d, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist2 = dx*dx + dy*dy
                    else:
                        dist2 = float('inf')
                    is_idle = (st == "idle")
                    pool.append((0 if is_idle else 1, dist2, getattr(d, "id", ""), d))
                pool.sort(key=lambda t: (t[0], t[1], t[2]))

                for i in range(min(needed_field, len(pool))):
                    _, _, _, d = pool[i]
                    assigned[d] = gid
                    current_total_protecting += 1
                    if current_total_protecting >= target_half:
                        break
                if current_total_protecting >= target_half:
                    break

        # 4d) Remaining drones -> idle or fallback
        for d in components:
            if d not in assigned:
                if "idle" in group_set:
                    assigned[d] = "idle"
                else:
                    assigned[d] = next(iter(group_set), None)

        # 5) Apply assignments (exactly one per drone)
        for d, g in assigned.items():
            if g is not None:
                environment.assign_group(d, g)