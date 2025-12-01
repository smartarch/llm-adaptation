from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved allocation:
        - Always fully protect highest-threat field using closest/least-disruptive drones.
        - Reserve drones that are already protecting fully-protected fields.
        - Greedily full-protect other fields by score (threat_level / need) using available drones.
        - If full protection is impossible for remaining fields, assign leftover drones as partial protection
          to highest-threat nearest fields.
        - Minimize stealing from other protectors; prefer idle drones first.
        """
        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        def dist_to_rect(drone, field):
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

        # Threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Helper: protecting group name
        def grp_for(fid):
            g = f"protecting {fid}"
            return g if g in group_ids else None

        # Build current protector/mover maps
        comps = list(components)
        protectors_by_field = {}
        movers_by_field = {}
        for f in fields:
            protectors_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id]
            movers_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == f.id]

        # Reserve drones that already fully protect their fields
        reserved = set()
        fully_protected_fields = set()
        for f in fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len(protectors_by_field.get(f.id, []))
            if required > 0 and cur >= required:
                fully_protected_fields.add(f.id)
                for c in protectors_by_field[f.id]:
                    reserved.add(c)

        # Available drones are those not reserved
        available = [c for c in comps if c not in reserved]

        # Pick top field by threat_level
        top_field = max(fields, key=lambda f: f.threat_level)
        top_group = grp_for(top_field.id)
        if top_group is None:
            # Can't protect (group missing) -> idle everyone
            for c in comps:
                environment.assign_group(c, idle_group)
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Count protectors/movers already for top field (reserved does not include them unless they were fully protecting other fields)
        protecting_top = [c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id]
        moving_top = [c for c in comps if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == top_field.id and c not in protecting_top]
        # Some of these might be in reserved if they were protecting a fully-protected field and target==top? Unlikely, but we treat reserved separately.
        current_top = set(protecting_top + moving_top)
        # Ensure we don't double-count reserved drones already assigned elsewhere
        current_top = set([c for c in current_top if c not in reserved])

        need = max(0, required_top - len(current_top))

        # Candidate selection for top field:
        # Prefer: protecting_top/moving_top (already included), then idle (closest), then moving to other fields (closest),
        # then protecting other fields but prefer from lower-threat fields (to minimize impact).
        candidates = []
        # Build map field threat for stealing preference
        field_threat_map = {f.id: f.threat_level for f in fields}

        for c in available:
            if c in current_top:
                continue
            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)
            if state == "idle":
                pr = 1
            elif state == "moving_to_field":
                # if moving to top, already handled; else moving to other
                pr = 2
            elif state == "protecting":
                # stealing from protecting others is last resort; prioritize stealing from low-threat fields
                # Use threat level of target as tie-breaker; lower threat -> better to steal
                target_threat = field_threat_map.get(target, 0) if target is not None else 0
                # We'll encode priority as 3 and use target_threat in sorting key
                pr = 3
            else:
                pr = 3
            d = dist_to_rect(c, top_field)
            # For protecting others we include target_threat for sort; for others target_threat=inf so they sort before protectors with high threat
            target_threat = field_threat_map.get(target, 0) if target is not None else 0
            candidates.append((pr, target_threat, d, c))

        # Sort: lower pr first, then lower target_threat (steal from lower threat fields first), then closer distance
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))

        selected_for_top = []
        if need > 0:
            for pr, tth, d, c in candidates:
                selected_for_top.append(c)
                if len(selected_for_top) >= need:
                    break

        final_top_set = set(current_top).union(selected_for_top)

        # Mark assignments so far: reserved drones -> their protect group; final_top_set -> top_group
        assignment = {}

        for c in reserved:
            # find the field they protect (their target_id)
            tid = getattr(c, "target_id", None)
            grp = grp_for(tid) if tid is not None else None
            assignment[c] = grp if grp is not None else idle_group

        for c in final_top_set:
            assignment[c] = top_group

        # Update available pool removing those assigned to top (but keep reserved already removed)
        available_after_top = [c for c in available if c not in final_top_set]

        # Now attempt to fully protect other fields greedily by score = threat / need (prefer small need)
        other_fields = [f for f in fields if f.id != top_field.id and f.id not in fully_protected_fields]
        # compute need for each
        field_needs = {}
        for f in other_fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len([c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id and c not in reserved and c not in final_top_set])
            need_f = max(0, required - cur)
            field_needs[f.id] = need_f

        # Score fields and sort
        candidate_fields = []
        for f in other_fields:
            need_f = field_needs[f.id]
            if need_f <= 0:
                # already satisfied among non-reserved; assign those protectors to that group (if not reserved)
                for c in [c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id and c not in reserved]:
                    assignment[c] = grp_for(f.id) or idle_group
                continue
            # avoid division by zero; use threat/need as score
            score = (f.threat_level / need_f) if need_f > 0 else 0
            candidate_fields.append(( -score, need_f, f ))  # negative to sort descending

        candidate_fields.sort()

        # Helper to allocate up to need_f drones to field f from available_after_top
        def allocate_to_field(f, need_f, avail_list):
            if need_f <= 0:
                return [], avail_list, True
            # Build candidates prioritizing existing movers/protectors to that field, then idle, then moving/protecting others
            cands = []
            for c in avail_list:
                state = getattr(c, "state", None)
                target = getattr(c, "target_id", None)
                # priority ordering for other fields: prefers movers/protectors to that field
                if state in ("protecting", "moving_to_field") and target == f.id:
                    pr = 0
                elif state == "idle":
                    pr = 1
                elif state == "moving_to_field":
                    pr = 2
                else:
                    pr = 3
                d = dist_to_rect(c, f)
                # Use (pr, d) sort
                cands.append((pr, d, c))
            cands.sort(key=lambda x: (x[0], x[1]))
            if len(cands) < need_f:
                return [], avail_list, False
            chosen = [c for (_, _, c) in cands[:need_f]]
            new_avail = [c for c in avail_list if c not in chosen]
            return chosen, new_avail, True

        # Greedily full-protect other fields where possible
        for neg_score, need_f, f in candidate_fields:
            chosen, available_after_top, success = allocate_to_field(f, need_f, available_after_top)
            if success:
                grp = grp_for(f.id) or idle_group
                for c in chosen:
                    assignment[c] = grp

        # After trying to fully protect others, if drones remain, use them for partial protection:
        # assign remaining drones to highest-threat nearest fields (partial helps)
        remaining = [c for c in comps if c not in assignment]
        if remaining:
            # sort fields by threat desc
            fields_by_threat = sorted(fields, key=lambda f: f.threat_level, reverse=True)
            for c in remaining:
                # choose nearest high-threat field (iterate fields_by_threat and pick nearest)
                best_field = None
                best_dist = float("inf")
                for f in fields_by_threat:
                    d = dist_to_rect(c, f)
                    if d < best_dist:
                        best_dist = d
                        best_field = f
                if best_field:
                    grp = grp_for(best_field.id) or idle_group
                    assignment[c] = grp
                else:
                    assignment[c] = idle_group

        # Finally, apply assignments (ensure every component is assigned exactly once)
        for c in comps:
            g = assignment.get(c, idle_group)
            # final safety: if group missing fallback to idle_group
            if g not in group_ids:
                g = idle_group
            environment.assign_group(c, g)