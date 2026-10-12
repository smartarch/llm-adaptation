from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group(field_id):
            return f"protecting {field_id}"

        idle_group = "idle"
        speed = 2.0  # drone speed (units per time)

        # Tunable weights
        alpha = 200.0  # weight for disruption cost (keep high to avoid harm)
        beta = 1.0     # weight for ETA (prefer faster arrivals)

        # Helpers
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_sq(a_x, a_y, b_x, b_y):
            dx = a_x - b_x
            dy = a_y - b_y
            return dx * dx + dy * dy

        def eta_from_loc_to(loc, tx, ty):
            if loc is None:
                return float("inf")
            d = math.sqrt(dist_sq(loc.x, loc.y, tx, ty))
            return d / speed

        # Gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats: assign all drones to idle
            for c in components:
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
            return

        # Deterministic order: sort by threat desc then id
        fields_sorted = sorted(fields, key=lambda f: (-f.threat_level, str(f.id)))
        top_field = fields_sorted[0]
        top_cx, top_cy = field_center(top_field)

        # Map current assignments by field id
        assigned_to_field = {f.id: [] for f in fields}
        for c in components:
            tid = getattr(c, "target_id", None)
            if tid in assigned_to_field:
                assigned_to_field[tid].append(c)

        # Identify fully protected fields and lock their drones
        fully_protected = set()
        for f in fields:
            req = getattr(f, "drones_for_full_protection", 0)
            if len(assigned_to_field.get(f.id, [])) >= req:
                fully_protected.add(f.id)

        locked_drones = set()
        locked_map = {}
        for fid in fully_protected:
            for c in assigned_to_field.get(fid, []):
                locked_drones.add(c)
                locked_map[c] = fid

        # Prepare decided assignments map
        decided = {}

        # Keep locked drones at their protecting group
        for c in locked_drones:
            decided[c] = protecting_group(locked_map[c])

        # Precompute assigned counts
        assigned_counts = {f.id: len(assigned_to_field.get(f.id, [])) for f in fields}

        # Stage 1: Fully protect top field
        top_req = getattr(top_field, "drones_for_full_protection", 0)
        top_current = len(assigned_to_field.get(top_field.id, []))
        need_top = max(0, top_req - top_current)

        # Keep those already targeting top
        for c in assigned_to_field.get(top_field.id, []):
            decided[c] = protecting_group(top_field.id)

        selected_for_top = set()
        if need_top > 0:
            # Candidates: unlocked and not already targeting top
            candidates = [c for c in components if c not in locked_drones and getattr(c, "target_id", None) != top_field.id]

            # compute disruption cost and ETA
            candidate_scores = []
            for c in candidates:
                tid = getattr(c, "target_id", None)
                state = getattr(c, "state", "")
                # disruption cost
                if tid is None:
                    disruption = 0.0
                elif tid not in assigned_counts:
                    disruption = 0.0
                else:
                    req_tid = getattr(next((f for f in fields if f.id == tid), None), "drones_for_full_protection", 0)
                    assigned = assigned_counts.get(tid, 0)
                    if assigned > req_tid:
                        disruption = 0.0
                    else:
                        # if removing this drone causes shortage, compute shortage magnitude
                        shortage_if_removed = max(0, req_tid - (assigned - 1))
                        # weigh by that field's threat
                        field_obj = next((f for f in fields if f.id == tid), None)
                        threat = getattr(field_obj, "threat_level", 0) if field_obj is not None else 0
                        disruption = shortage_if_removed * (threat + 0.01)
                # small penalty for currently protecting to avoid pulling active protectors
                protect_penalty = 0.15 if state == "protecting" else 0.0
                disruption_cost = disruption + protect_penalty

                loc = getattr(c, "location", None)
                eta = eta_from_loc_to(loc, top_cx, top_cy)
                # score combined
                score = disruption_cost * alpha + eta * beta
                # tie-breakers: prefer idle/moving then closer distance
                state_rank = 0 if state == "idle" else (1 if state == "moving_to_field" else 2)
                d2 = dist_sq(loc.x, loc.y, top_cx, top_cy) if loc is not None else float("inf")
                candidate_scores.append((score, disruption_cost, state_rank, eta, d2, c))

            # sort and pick lowest-score need_top
            candidate_scores.sort(key=lambda t: (t[0], t[1], t[2], t[3], t[4]))
            for tpl in candidate_scores[:need_top]:
                c = tpl[5]
                selected_for_top.add(c)
                # adjust assigned_counts for the field we take from
                tid = getattr(c, "target_id", None)
                if tid in assigned_counts:
                    assigned_counts[tid] = max(0, assigned_counts[tid] - 1)

        # Apply assignments for top
        for c in selected_for_top:
            decided[c] = protecting_group(top_field.id)

        # Stage 2: Greedily fully protect other fields where benefit per drone is highest
        # Build remaining pool (not locked, not decided)
        remaining = [c for c in components if c not in decided and c not in locked_drones]

        # Recompute current counts reflecting moved drones and kept targets
        current_counts = {}
        for f in fields:
            # count drones that remain targeting f (not stolen for top and not locked elsewhere)
            lst = []
            for c in assigned_to_field.get(f.id, []):
                if c in decided and decided[c] != protecting_group(f.id):
                    continue
                if c in locked_drones and locked_map.get(c) == f.id:
                    lst.append(c)
                elif c not in decided:
                    lst.append(c)
                elif decided.get(c) == protecting_group(f.id):
                    lst.append(c)
            current_counts[f.id] = len(lst)
        # Also add drones we explicitly decided to protect some fields
        for c, g in decided.items():
            if g.startswith("protecting "):
                fid_str = g[len("protecting "):]
                for key in list(current_counts.keys()):
                    if str(key) == str(fid_str):
                        if c not in assigned_to_field.get(key, []):
                            current_counts[key] = current_counts.get(key, 0) + 1

        # Helper to pick k best drones from pool for a given field (prefer idle/moving and low disruption)
        def pick_best_for_field(field_obj, pool, k):
            tx, ty = field_center(field_obj)
            scored = []
            for c in pool:
                state = getattr(c, "state", "")
                state_rank = 0 if state == "idle" else (1 if state == "moving_to_field" else 2)
                tid = getattr(c, "target_id", None)
                # disruption metric similar to above (smaller is better)
                if tid is None:
                    disruption = 0.0
                elif tid not in current_counts:
                    disruption = 0.0
                else:
                    req_tid = getattr(next((f for f in fields if f.id == tid), None), "drones_for_full_protection", 0)
                    assigned = current_counts.get(tid, 0)
                    if assigned > req_tid:
                        disruption = 0.0
                    else:
                        shortage_if_removed = max(0, req_tid - (assigned - 1))
                        field_obj2 = next((f for f in fields if f.id == tid), None)
                        threat2 = getattr(field_obj2, "threat_level", 0) if field_obj2 is not None else 0
                        disruption = shortage_if_removed * (threat2 + 0.01)
                loc = getattr(c, "location", None)
                eta = eta_from_loc_to(loc, tx, ty)
                d2 = dist_sq(loc.x, loc.y, tx, ty) if loc is not None else float("inf")
                # Choose by (disruption, state_rank, eta, distance)
                scored.append((disruption, state_rank, eta, d2, c))
            scored.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
            return [t[4] for t in scored[:k]]

        # Compute value-per-drone for fields: threat / need
        other_fields = [f for f in fields_sorted[1:]]  # exclude top
        # Loop to greedily pick fields we can fully protect
        available = list(remaining)  # mutable pool
        while True:
            candidates = []
            for f in other_fields:
                fid = f.id
                req = getattr(f, "drones_for_full_protection", 0)
                have = current_counts.get(fid, 0)
                need = max(0, req - have)
                if need <= 0:
                    continue
                if need <= len(available):
                    value = getattr(f, "threat_level", 0) / float(need) if need > 0 else 0
                    candidates.append((value, getattr(f, "threat_level", 0), need, f))
            if not candidates:
                break
            # pick best value-per-drone (tie-break by threat then id)
            candidates.sort(key=lambda t: (-t[0], -t[1], str(getattr(t[3], "id", ""))))
            value, threat_v, need, chosen_field = candidates[0]
            # pick best 'need' drones for this field
            picked = pick_best_for_field(chosen_field, available, need)
            if not picked:
                break
            for c in picked:
                decided[c] = protecting_group(chosen_field.id)
                if c in available:
                    available.remove(c)
                # update counts
                tid = getattr(c, "target_id", None)
                if tid in current_counts:
                    current_counts[tid] = max(0, current_counts.get(tid, 0) - 1)
                current_counts[chosen_field.id] = current_counts.get(chosen_field.id, 0) + 1

        # Remaining drones: give partial coverage -> assign one-per-highest-threat remaining fields
        available = [c for c in components if c not in decided and c not in locked_drones]
        if available:
            partial_targets = [f for f in fields_sorted if f.id != top_field.id and f.id not in fully_protected]
            # assign at most one drone per field, in threat order
            for f in partial_targets:
                if not available:
                    break
                fid = f.id
                req = getattr(f, "drones_for_full_protection", 0)
                have = current_counts.get(fid, 0)
                if have >= req:
                    continue
                # pick one best drone
                picked = pick_best_for_field(f, available, 1)
                if not picked:
                    continue
                c = picked[0]
                decided[c] = protecting_group(fid)
                if c in available:
                    available.remove(c)
                current_counts[fid] = current_counts.get(fid, 0) + 1

        # Any still remaining -> idle
        for c in components:
            if c not in decided:
                decided[c] = idle_group

        # Ensure group_ids validity and assign
        for c, g in decided.items():
            if g not in group_ids:
                # fallback to idle if present
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
                elif group_ids:
                    environment.assign_group(c, group_ids[0])
                else:
                    # no valid groups; skip
                    pass
            else:
                environment.assign_group(c, g)