from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, comp, field):
        cx, cy = self._field_center(field)
        dx = comp.location.x - cx
        dy = comp.location.y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        comps = list(components)
        comp_index = {c: i for i, c in enumerate(comps)}  # deterministic tie-break

        # Helper to form protecting group name
        def protect_group(field_id):
            return f"protecting {field_id}"

        # Collect fields with positive threat
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle everyone
        if not threatened:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        # Choose top field (highest threat, tie by id)
        max_threat = max(f.threat_level for f in threatened)
        top_candidates = [f for f in threatened if f.threat_level == max_threat]
        top_field = sorted(top_candidates, key=lambda f: f.id)[0]
        top_group = protect_group(top_field.id)
        if top_group not in group_ids:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Partition components into categories and build quick access
        already_targeting = {}  # field_id -> list of comps targeting it (protecting or moving_to_field)
        for f in environment.fields:
            already_targeting[f.id] = []
        for c in comps:
            tid = getattr(c, "target_id", None)
            state = getattr(c, "state", None)
            if tid is not None and state in ("moving_to_field", "protecting"):
                if tid in already_targeting:
                    already_targeting[tid].append(c)

        # Assignment map we'll fill
        assignment = {}

        # --- Top field: keep its already-targeting drones and add closest drones as needed ---
        top_already = list(already_targeting.get(top_field.id, []))
        # Keep all already-targeting drones for top (per requirement to keep those)
        selected_top = list(top_already)

        # Build pool of other components not already selected for top
        pool = [c for c in comps if c not in selected_top]

        # If need more drones for top, prefer idle first, then moving_to_field, then others by distance
        need_top = max(0, required_top - len(selected_top))
        if need_top > 0 and pool:
            def state_priority(c):
                s = getattr(c, "state", None)
                if s == "idle":
                    return 0
                if s == "moving_to_field":
                    return 1
                return 2  # protecting or unknown
            pool_sorted = sorted(pool, key=lambda c: (state_priority(c), self._distance(c, top_field), comp_index[c]))
            take = pool_sorted[:need_top]
            selected_top.extend(take)
            # remove taken from pool
            taken_set = set(take)
            pool = [c for c in pool if c not in taken_set]

        # Assign selected_top to top_group
        for c in comps:
            if c in selected_top:
                assignment[c] = top_group

        # --- Greedily protect other fields by descending threat ---
        others = [f for f in threatened if f.id != top_field.id]
        others.sort(key=lambda f: (-f.threat_level, f.id))

        # pool currently contains components not assigned to top_group
        available = list(pool)

        for f in others:
            grp = protect_group(f.id)
            if grp not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # Count comps already targeting this field (and not already used for top)
            preassigned = [c for c in already_targeting.get(f.id, []) if c in available]
            # Keep those preassigned (they are already on their way)
            assigned_here = list(preassigned)
            # Remove them from available
            assigned_set = set(assigned_here)
            available = [c for c in available if c not in assigned_set]

            # If still need more to reach required, pick closest from available (prefer idle then moving)
            need = max(0, required - len(assigned_here))
            if need > 0:
                def state_priority(c):
                    s = getattr(c, "state", None)
                    if s == "idle":
                        return 0
                    if s == "moving_to_field":
                        return 1
                    return 2
                avail_sorted = sorted(available, key=lambda c: (state_priority(c), self._distance(c, f), comp_index[c]))
                if len(avail_sorted) >= need:
                    to_assign = avail_sorted[:need]
                    assigned_here.extend(to_assign)
                    taken_set = set(to_assign)
                    available = [c for c in available if c not in taken_set]
                else:
                    # not enough drones to fully protect this field; skip full protection to avoid partial inefficiency
                    # restore preassigned back to available (they remain free for other decisions)
                    # Note: we keep them targeting the same field (they are already en-route/protecting),
                    # but we will not explicitly assign them now to avoid claiming full protection.
                    # Instead, they will be left assigned below if not used elsewhere.
                    # Put preassigned back to available for now (they might be used for other higher-priority fields)
                    available.extend(assigned_here)
                    continue

            # Assign all assigned_here to this field's group
            for c in assigned_here:
                assignment[c] = grp

        # After attempting full protection, remaining drones in 'available' are leftovers
        leftovers = list(available)

        # Assign leftovers per-drone to best remaining field for partial protection (heuristic)
        if leftovers:
            candidates = [f for f in threatened if f.id != top_field.id and protect_group(f.id) in group_ids]
            if candidates:
                for c in leftovers:
                    best_field = None
                    best_key = None
                    for f in candidates:
                        req = max(1, int(getattr(f, "drones_for_full_protection", 1)))
                        # prefer higher threat per drone and closer distance
                        score = - (f.threat_level / req)
                        dist = self._distance(c, f)
                        key = (score, dist, f.id)
                        if best_key is None or key < best_key:
                            best_key = key
                            best_field = f
                    if best_field is not None:
                        assignment[c] = protect_group(best_field.id)
                    else:
                        assignment[c] = "idle"
            else:
                for c in leftovers:
                    assignment[c] = "idle"

        # Ensure every component has an explicit assignment (default idle)
        for c in comps:
            grp = assignment.get(c, "idle")
            environment.assign_group(c, grp)