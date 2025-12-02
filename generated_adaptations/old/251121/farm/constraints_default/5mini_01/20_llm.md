Reasoning and strategy

Summary goal: reduce average damage by protecting fields in a way that maximizes prevented damage per drone while respecting rules:
- The single most threatened field must always be fully protected (keep its current protectors and use closest drones; steal minimally if necessary).
- Preserve protecting drones where possible (inertia) to avoid churn.
- Use at least half the drones for protection when threats exist.

Observation from earlier experiments: completing a field (bringing it to full protection) is often far more effective than scattering drones for partial protection. So the algorithm below is a hybrid that:

1. Force-completes the top-threat field (mandatory).
2. Greedily complete additional fields when the "adjusted benefit per required drone" is high. For each candidate field we compute:
   - benefit_full = field.threat_level (higher means preventing more damage)
   - cost = number of additional drones required to fully protect it
   - avg_travel_time for the cheapest 'cost' available drones
   - adjusted_score = (benefit_full / max(1, cost)) / (1 + avg_travel_time)
   We prefer to complete fields with the highest adjusted_score first and only complete them if there are enough available drones (or if conservative stealing from surplus protectors is possible).
   We also add a completion_boost factor ( > 1 ) so that completing a field is favored over equivalent partial assignments.
3. After finishing sensible completions, assign the remaining drones individually by marginal_value_per_time:
   score(d, f) = (threat_level / max(1, drones_for_full_protection)) / (1 + travel_time)
   with a small boost if drone is already moving to that field.
4. Ensure at least half the drones are protecting; if not, assign remaining unassigned drones to nearest fields and as a last resort steal minimally from fields with surplus protectors.
5. Explicitly assign every drone to exactly one group.

This approach tries to finish high-value, low-cost fields first, then uses remaining drones to provide marginal gains, while preserving stability and obeying the mandatory top-field rule.

Code (single Python block):

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total_drones = len(drones)
        speed = 2.0

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, x, y):
            dx = getattr(drone.location, "x", 0) - x
            dy = getattr(drone.location, "y", 0) - y
            return math.hypot(dx, dy)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        # Minimum protecting drones desired
        min_protect = ceil(total_drones / 2.0)

        # Sort fields by descending threat (deterministic tie-break by id)
        threatened.sort(key=lambda f: (f.threat_level, f.id), reverse=True)

        # Preserve existing protectors by default
        assigned = {}
        for d in drones:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                assigned[d] = f"protecting {d.target_id}"
            else:
                assigned[d] = None

        # Build field info dictionary
        field_info = {}
        for f in threatened:
            req = int(getattr(f, "drones_for_full_protection", 0))
            grp = f"protecting {f.id}"
            cur = [d for d, g in assigned.items() if g == grp]
            rem = max(0, req - len(cur))
            marginal = (getattr(f, "threat_level", 0) / max(1, req)) if req > 0 else getattr(f, "threat_level", 0)
            field_info[f.id] = {
                "field": f,
                "group": grp,
                "required": req,
                "current": cur[:],
                "remaining": rem,
                "marginal": marginal,
                "center": center_of(f)
            }

        def total_protecting_count():
            return sum(1 for g in assigned.values() if g is not None)

        # 1) Mandatory: fully protect the top-threat field (must succeed, stealing if necessary)
        top = threatened[0]
        top_id = top.id
        top_grp = f"protecting {top_id}"
        top_info = field_info[top_id]
        need_top = max(0, top_info["required"] - len(top_info["current"]))
        if need_top > 0:
            cx, cy = top_info["center"]
            # Prefer unassigned drones close to top; boost those moving to it
            unassigned = [d for d, g in assigned.items() if g is None]
            def top_key(d):
                distance = dist(d, cx, cy)
                travel_time = distance / speed
                score = 1.0 / (1.0 + travel_time)
                if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                    score *= 1.25
                return (-score, distance)
            unassigned.sort(key=top_key)

            selected = []
            for d in unassigned:
                if need_top <= 0:
                    break
                selected.append(d)
                need_top -= 1

            # If still need, steal minimally from other fields (prefer surplus then low threat then close)
            if need_top > 0:
                steal_pool = []
                for fid, info in field_info.items():
                    if fid == top_id:
                        continue
                    for protector in info["current"]:
                        distance = dist(protector, cx, cy)
                        surplus = len(info["current"]) - info["required"]
                        steal_pool.append((-surplus, getattr(info["field"], "threat_level", 0), distance, protector, fid))
                steal_pool.sort(key=lambda x: (x[0], x[1], x[2]))
                for _, _, _, protector, src_fid in steal_pool:
                    if need_top <= 0:
                        break
                    if protector in field_info[src_fid]["current"]:
                        field_info[src_fid]["current"].remove(protector)
                        if field_info[src_fid]["required"] > 0:
                            if len(field_info[src_fid]["current"]) < field_info[src_fid]["required"]:
                                field_info[src_fid]["remaining"] = field_info[src_fid]["required"] - len(field_info[src_fid]["current"])
                    selected.append(protector)
                    assigned[protector] = top_grp
                    need_top -= 1

            # finalize top assignments
            for d in selected:
                assigned[d] = top_grp
                if d not in top_info["current"]:
                    top_info["current"].append(d)
            top_info["remaining"] = max(0, top_info["required"] - len(top_info["current"]))

        # 2) Completion-first greedy using adjusted benefit per drone
        # completion_boost >1 favors completing fields (empirically useful)
        completion_boost = 1.4

        def available_drones():
            return [d for d, g in assigned.items() if g is None]

        # helper to pick k closest available drones for a field
        def pick_k_closest(fid, available, k):
            cx, cy = field_info[fid]["center"]
            available_sorted = sorted(available, key=lambda d: dist(d, cx, cy))
            chosen = available_sorted[:k]
            if not chosen:
                return chosen, float('inf')
            avg_time = sum(dist(d, cx, cy) for d in chosen) / (len(chosen) * speed)
            return chosen, avg_time

        # Repeat: compute score for each field that has remaining need and can be finished with available drones
        while True:
            avail = available_drones()
            if not avail:
                break
            candidates = []
            for fid, info in field_info.items():
                if fid == top_id:
                    continue
                need = info["remaining"]
                if need <= 0:
                    continue
                if need > len(avail):
                    continue
                chosen, avg_time = pick_k_closest(fid, avail, need)
                if not chosen:
                    continue
                # adjusted score: value per required drone, penalized by travel time
                score = (info["field"].threat_level / max(1, need)) / (1.0 + avg_time)
                score *= completion_boost
                # small boost for chosen drones already moving to that field
                moving_count = sum(1 for d in chosen if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid)
                score *= (1.0 + 0.12 * moving_count)
                candidates.append((score, fid, chosen))
            if not candidates:
                break
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_fid, best_chosen = candidates[0]
            # assign chosen drones to best_fid
            for d in best_chosen:
                assigned[d] = field_info[best_fid]["group"]
                field_info[best_fid]["current"].append(d)
                if field_info[best_fid]["remaining"] > 0:
                    field_info[best_fid]["remaining"] -= 1

        # 3) Per-drone marginal assignment for remaining drones
        unassigned_now = [d for d, g in assigned.items() if g is None]
        per_drone_candidates = []
        for d in unassigned_now:
            best_score = -1
            best_fid = None
            for fid, info in field_info.items():
                cx, cy = info["center"]
                distance = dist(d, cx, cy)
                travel_time = distance / speed
                score = info["marginal"] / (1.0 + travel_time)
                if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid:
                    score *= 1.15
                if score > best_score:
                    best_score = score
                    best_fid = fid
            if best_fid is not None:
                per_drone_candidates.append((best_score, d, best_fid))
        per_drone_candidates.sort(key=lambda x: x[0], reverse=True)
        for score, d, fid in per_drone_candidates:
            if assigned[d] is not None:
                continue
            assigned[d] = field_info[fid]["group"]
            field_info[fid]["current"].append(d)
            if field_info[fid]["remaining"] > 0:
                field_info[fid]["remaining"] -= 1

        # 4) Ensure at least half the drones protecting: assign nearest or steal conservatively if needed
        if total_protecting_count() < min_protect:
            # assign nearest fields for remaining unassigned drones
            still_unassigned = [d for d, g in assigned.items() if g is None]
            def nearest_field_for_drone(d):
                best = None
                best_dist = float('inf')
                for fid, info in field_info.items():
                    cx, cy = info["center"]
                    dt = dist(d, cx, cy)
                    if dt < best_dist:
                        best_dist = dt
                        best = fid
                return best, best_dist
            still_unassigned.sort(key=lambda d: nearest_field_for_drone(d)[1])
            for d in still_unassigned:
                if total_protecting_count() >= min_protect:
                    break
                best_fid, _ = nearest_field_for_drone(d)
                if best_fid is None:
                    continue
                assigned[d] = field_info[best_fid]["group"]
                field_info[best_fid]["current"].append(d)
                if field_info[best_fid]["remaining"] > 0:
                    field_info[best_fid]["remaining"] -= 1
            # if still short, steal from fields with surplus (prefer low-threat)
            if total_protecting_count() < min_protect:
                need = min_protect - total_protecting_count()
                steal_pool = []
                for fid, info in field_info.items():
                    if fid == top_id:
                        continue
                    surplus = len(info["current"]) - info["required"]
                    for protector in info["current"]:
                        steal_pool.append(( -surplus, getattr(info["field"], "threat_level", 0), protector, fid))
                steal_pool.sort(key=lambda x: (x[0], x[1]))
                for _, _, protector, src_fid in steal_pool:
                    if need <= 0:
                        break
                    if protector in field_info[src_fid]["current"]:
                        field_info[src_fid]["current"].remove(protector)
                        if field_info[src_fid]["required"] > 0:
                            if len(field_info[src_fid]["current"]) < field_info[src_fid]["required"]:
                                field_info[src_fid]["remaining"] = field_info[src_fid]["required"] - len(field_info[src_fid]["current"])
                    # assign protector to best target by marginal/time
                    best_tgt = None
                    best_score = -1
                    for fid, info in field_info.items():
                        if fid == src_fid:
                            continue
                        cx, cy = info["center"]
                        travel_time = dist(protector, cx, cy) / speed
                        score = info["marginal"] / (1.0 + travel_time)
                        if score > best_score:
                            best_score = score
                            best_tgt = fid
                    if best_tgt is None:
                        assigned[protector] = "idle"
                    else:
                        assigned[protector] = field_info[best_tgt]["group"]
                        field_info[best_tgt]["current"].append(protector)
                        if field_info[best_tgt]["remaining"] > 0:
                            field_info[best_tgt]["remaining"] -= 1
                    need -= 1

        # Final: explicitly assign everyone
        for d in drones:
            final = assigned[d]
            if final is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, final)