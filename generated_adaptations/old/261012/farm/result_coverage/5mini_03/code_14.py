from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Always fully protect the highest-threat field using closest drones by arrival time (distance to rectangle / speed).
        - Prefer recruiting idle drones first, then drones moving (to other fields), and only as last resort steal from protectors of other fields,
          preferring to steal from fields with lower threat.
        - Keep drones that already fully protect their fields in place.
        - After securing the top field, use remaining idle/moving drones (but not other protectors) to fully protect additional fields
          in descending threat order if possible (no stealing).
        - All unassigned drones get 'idle'.
        """
        DRONE_SPEED = 2.0

        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        def distance_to_rect(drone, field):
            x = getattr(drone.location, "x", 0)
            y = getattr(drone.location, "y", 0)
            left = getattr(field, "left", 0)
            right = getattr(field, "right", 0)
            top = getattr(field, "top", 0)
            bottom = getattr(field, "bottom", 0)
            nx = clamp(x, left, right)
            ny = clamp(y, top, bottom)
            return hypot(x - nx, y - ny)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else idle_group

        # Gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Quick group name helper
        def protect_group_name(field_id):
            g = f"protecting {field_id}"
            return g if g in group_ids else None

        comps = list(components)

        # Build maps of protectors and movers per field
        protectors_by_field = {}
        movers_by_field = {}
        for f in fields:
            protectors_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id]
            movers_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == f.id]

        # Reserve protectors of already fully-protected fields
        reserved = set()
        fully_protected_fields = set()
        for f in fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len(protectors_by_field.get(f.id, []))
            if required > 0 and cur >= required:
                fully_protected_fields.add(f.id)
                for c in protectors_by_field[f.id]:
                    reserved.add(c)

        # Determine top field
        top_field = max(fields, key=lambda f: f.threat_level)
        top_group = protect_group_name(top_field.id)
        if top_group is None:
            # If group missing, idle everyone
            for c in comps:
                environment.assign_group(c, idle_group)
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones already protecting or moving to top field (but exclude any that are reserved protecting other fully-protected fields)
        protecting_top = [c for c in protectors_by_field.get(top_field.id, []) if c not in reserved]
        moving_top = [c for c in movers_by_field.get(top_field.id, []) if c not in reserved and c not in protecting_top]

        committed_top = list(protecting_top) + list(moving_top)
        committed_top_set = set(committed_top)
        current_top_count = len(committed_top_set)
        need_top = max(0, required_top - current_top_count)

        # Build candidate lists from drones not reserved and not already committed to top
        available = [c for c in comps if c not in reserved and c not in committed_top_set]

        idle_cands = []
        moving_cands = []
        protecting_cands = []  # protectors of other (non-fully) fields

        # Map field threat for steal priority
        field_threat = {f.id: f.threat_level for f in fields}

        for c in available:
            state = getattr(c, "state", None)
            tid = getattr(c, "target_id", None)
            dist = distance_to_rect(c, top_field)
            arrival = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')
            if state == "idle":
                idle_cands.append((arrival, c))
            elif state == "moving_to_field":
                moving_cands.append((arrival, c))
            else:
                # protecting others — consider only if they protect non-fully-protected fields
                if tid is not None and tid not in fully_protected_fields:
                    # steal priority: prefer lower-threat fields (so sort by threat ascending)
                    protecting_cands.append((field_threat.get(tid, 0), arrival, c))
                else:
                    # protecting a fully protected field (should be in reserved), or unknown target: treat as last-resort with high threat
                    protecting_cands.append((float('inf'), arrival, c))

        idle_cands.sort(key=lambda x: x[0])
        moving_cands.sort(key=lambda x: x[0])
        protecting_cands.sort(key=lambda x: (x[0], x[1]))  # sort by target field threat (low first), then arrival

        selected_for_top = []
        if need_top > 0:
            # pick from idle first
            for arrival, c in idle_cands:
                selected_for_top.append(c)
                if len(selected_for_top) >= need_top:
                    break
            # then movers
            if len(selected_for_top) < need_top:
                for arrival, c in moving_cands:
                    selected_for_top.append(c)
                    if len(selected_for_top) >= need_top:
                        break
            # finally steal from protectors if still needed
            if len(selected_for_top) < need_top:
                for threat_val, arrival, c in protecting_cands:
                    selected_for_top.append(c)
                    if len(selected_for_top) >= need_top:
                        break

        final_top_set = set(committed_top_set).union(selected_for_top)

        # Mark assignments: reserved protectors remain where they are; final_top_set -> top_group
        assignment = {}

        for c in reserved:
            tid = getattr(c, "target_id", None)
            grp = protect_group_name(tid) if tid is not None else None
            assignment[c] = grp if grp is not None else idle_group

        for c in final_top_set:
            assignment[c] = top_group

        # Update available pool after top assignment: exclude reserved and final_top_set and also exclude any already assigned
        remaining_pool = [c for c in comps if c not in assignment]

        # Now try to fully protect additional fields using only non-protector drones:
        # Build a pool of drones that we may use for additional fields without stealing other protectors:
        # allow only drones that are currently idle or moving (not protecting)
        pool_for_others = [c for c in remaining_pool if getattr(c, "state", None) in ("idle", "moving_to_field")]

        # Build list of other fields (exclude top and fully_protected_fields)
        other_fields = [f for f in fields if f.id != top_field.id and f.id not in fully_protected_fields]

        # For each other field, compute remaining need accounting for current protectors (excluding any we may have assigned to top)
        # Note: ensure we don't count reserved protectors as available
        def current_protect_count(field):
            return len([c for c in protectors_by_field.get(field.id, []) if c not in reserved and c not in final_top_set])

        # Score fields by threat per extra drone (prefer high ratio) and smaller need
        candidates = []
        for f in other_fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = current_protect_count(f)
            need = max(0, required - cur)
            if need == 0:
                # already satisfied (non-reserved protectors), keep those protectors assigned
                grp = protect_group_name(f.id) or idle_group
                for c in [c for c in protectors_by_field.get(f.id, []) if c not in reserved and c not in final_top_set]:
                    assignment[c] = grp
                continue
            # compute score = threat / need (higher better)
            score = (f.threat_level / need) if need > 0 else 0
            candidates.append((-score, need, f))
        candidates.sort()

        # Try to fully protect as many as possible using pool_for_others
        for neg_score, need_f, f in candidates:
            if len(pool_for_others) < need_f:
                continue
            # choose best candidates from pool_for_others by arrival time to that field
            cands = []
            for c in pool_for_others:
                dist = distance_to_rect(c, f)
                atime = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')
                cands.append((atime, c))
            cands.sort(key=lambda x: x[0])
            chosen = [c for _, c in cands[:need_f]]
            # assign them
            grp = protect_group_name(f.id) or idle_group
            for c in chosen:
                assignment[c] = grp
            # remove chosen from pool_for_others and remaining_pool
            pool_for_others = [c for c in pool_for_others if c not in chosen]
            remaining_pool = [c for c in remaining_pool if c not in chosen]

        # Any drones still unassigned: for safety, assign idle (do not steal protectors)
        for c in comps:
            if c in assignment:
                g = assignment[c]
                if g not in group_ids:
                    g = idle_group
                environment.assign_group(c, g)
            else:
                environment.assign_group(c, idle_group)