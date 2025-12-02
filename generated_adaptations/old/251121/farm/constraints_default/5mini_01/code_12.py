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

        min_protect = ceil(total_drones / 2.0)

        # Sort by threat desc (deterministic tie-break by id)
        threatened.sort(key=lambda f: (f.threat_level, f.id), reverse=True)

        # Initialize assignment preserving existing protectors
        assigned = {}
        for d in drones:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                assigned[d] = f"protecting {d.target_id}"
            else:
                assigned[d] = None

        # Prepare field info
        field_info = {}
        for f in threatened:
            req = int(getattr(f, "drones_for_full_protection", 0))
            grp = f"protecting {f.id}"
            current = [d for d, g in assigned.items() if g == grp]
            remaining = max(0, req - len(current))
            marginal = (getattr(f, "threat_level", 0) / max(1, req)) if req > 0 else getattr(f, "threat_level", 0)
            center = center_of(f)
            field_info[f.id] = {
                "field": f,
                "group": grp,
                "required": req,
                "current": current[:],
                "remaining": remaining,
                "marginal": marginal,
                "center": center
            }

        # Utility counts
        def total_protecting_count():
            return sum(1 for g in assigned.values() if g is not None)

        # 1) Mandatory: ensure top field fully protected (force if necessary)
        top = threatened[0]
        top_id = top.id
        top_grp = f"protecting {top_id}"
        top_info = field_info[top_id]
        need_top = max(0, top_info["required"] - len(top_info["current"]))
        if need_top > 0:
            cx, cy = top_info["center"]
            # Prefer unassigned drones closest to top (boost those already moving to it)
            unassigned = [d for d, g in assigned.items() if g is None]
            def top_key(d):
                distance = dist(d, cx, cy)
                score = 1.0 / (1.0 + distance / speed)
                if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                    score *= 1.2
                return (-score, distance)
            unassigned.sort(key=top_key)
            selected = []
            for d in unassigned:
                if need_top <= 0:
                    break
                selected.append(d)
                need_top -= 1
            # If still lacking, steal minimally from other fields: prefer low-threat and those with surplus (i.e., have more than required)
            if need_top > 0:
                steal_pool = []
                for fid, info in field_info.items():
                    if fid == top_id:
                        continue
                    # gather protectors that could be stolen; prefer those from fields with surplus
                    for protector in info["current"]:
                        # surplus if len(current) > required
                        surplus = len(info["current"]) - info["required"]
                        # compute distance to top to prefer close drones
                        distance = dist(protector, cx, cy)
                        steal_pool.append((surplus, getattr(info["field"], "threat_level", 0), distance, protector, fid))
                # Sort: prefer surplus (higher surplus first), then lower threat, then closer
                steal_pool.sort(key=lambda x: (-x[0], x[1], x[2]))
                for surplus, src_threat, distance, protector, src_fid in steal_pool:
                    if need_top <= 0:
                        break
                    # only steal if it won't break a field that had exactly required protectors unless absolutely necessary
                    safe_to_steal = surplus > 0
                    if not safe_to_steal:
                        # allow stealing only if no other choice (we need to fill top)
                        pass
                    # perform steal
                    if protector in field_info[src_fid]["current"]:
                        field_info[src_fid]["current"].remove(protector)
                        # update remaining for source if needed
                        if field_info[src_fid]["required"] > 0:
                            if len(field_info[src_fid]["current"]) < field_info[src_fid]["required"]:
                                field_info[src_fid]["remaining"] = field_info[src_fid]["required"] - len(field_info[src_fid]["current"])
                    selected.append(protector)
                    assigned[protector] = top_grp
                    need_top -= 1
            # finalize assignment to top
            for d in selected:
                assigned[d] = top_grp
                if d not in top_info["current"]:
                    top_info["current"].append(d)
            top_info["remaining"] = max(0, top_info["required"] - len(top_info["current"]))

        # 2) Greedily fully protect as many remaining fields as possible using available drones
        # Repeat: compute score for each field = (threat / drones_needed) / (1 + avg_travel_time_of_selected), where selected are the needed closest available drones
        def get_closest_k_drones(field_id, available, k):
            cx, cy = field_info[field_id]["center"]
            # sort by distance
            lst = sorted(available, key=lambda d: dist(d, cx, cy))
            chosen = lst[:k]
            if not chosen:
                return chosen, float('inf')
            avg_time = sum(dist(d, cx, cy) for d in chosen) / (len(chosen) * speed)
            return chosen, avg_time

        # available pool: drones with assigned == None
        def available_drones():
            return [d for d, g in assigned.items() if g is None]

        # Fields eligible for full protection: remaining > 0
        while True:
            avail = available_drones()
            if not avail:
                break
            # Build candidate list (field_id -> (score, selected_drones))
            candidates = []
            for fid, info in field_info.items():
                if fid == top_id:
                    continue
                need = info["remaining"]
                if need <= 0:
                    continue
                # can't protect if need > len(avail) but may still consider if combined with surplus stealing (skip here)
                if need > len(avail):
                    continue
                selected, avg_time = get_closest_k_drones(fid, avail, need)
                if not selected:
                    continue
                # compute score; boost if some of selected are already moving to that field
                moving_boost = 1.0 + 0.15 * sum(1 for d in selected if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid)
                score = (info["field"].threat_level / max(1, need)) / (1.0 + avg_time)
                score *= moving_boost
                candidates.append((score, fid, selected, avg_time))
            if not candidates:
                break
            # pick best candidate
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_fid, best_selected, _ = candidates[0]
            # assign those drones to that field
            for d in best_selected:
                assigned[d] = field_info[best_fid]["group"]
                field_info[best_fid]["current"].append(d)
            field_info[best_fid]["remaining"] = max(0, field_info[best_fid]["required"] - len(field_info[best_fid]["current"]))
            # continue loop to consider next field

        # 3) If still below min_protect, assign remaining unassigned drones greedily by marginal/time to any field (partial allowed)
        if total_protecting_count() < min_protect:
            avail = available_drones()
            # build per-drone best target list
            drone_targets = []
            for d in avail:
                best = None
                best_score = -1
                for fid, info in field_info.items():
                    cx, cy = info["center"]
                    travel_time = dist(d, cx, cy) / speed
                    # marginal per time (even if field already full, allow partial protection)
                    score = info["marginal"] / (1.0 + travel_time)
                    if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid:
                        score *= 1.1
                    if score > best_score:
                        best_score = score
                        best = fid
                if best is not None:
                    drone_targets.append((best_score, d, best))
            drone_targets.sort(key=lambda x: x[0], reverse=True)
            for score, d, fid in drone_targets:
                if total_protecting_count() >= min_protect:
                    break
                if assigned[d] is not None:
                    continue
                assigned[d] = field_info[fid]["group"]
                field_info[fid]["current"].append(d)
                if field_info[fid]["remaining"] > 0:
                    field_info[fid]["remaining"] -= 1

        # 4) Conservative stealing to reach min_protect if still not met:
        if total_protecting_count() < min_protect:
            need = min_protect - total_protecting_count()
            # steal only from fields (excluding top) that have surplus (len(current) > required)
            steal_candidates = []
            for fid, info in field_info.items():
                if fid == top_id:
                    continue
                surplus = len(info["current"]) - info["required"]
                if surplus <= 0:
                    continue
                for protector in info["current"]:
                    # don't pick the same protector multiple times
                    steal_candidates.append((getattr(info["field"], "threat_level", 0), protector, fid))
            # Prefer stealing from lowest-threat fields (so sort ascending by threat)
            steal_candidates.sort(key=lambda x: (x[0], x[1].__hash__()))
            for _, protector, src_fid in steal_candidates:
                if need <= 0:
                    break
                # remove protector from source
                if protector in field_info[src_fid]["current"]:
                    field_info[src_fid]["current"].remove(protector)
                    if field_info[src_fid]["required"] > 0:
                        if len(field_info[src_fid]["current"]) < field_info[src_fid]["required"]:
                            field_info[src_fid]["remaining"] = field_info[src_fid]["required"] - len(field_info[src_fid]["current"])
                # assign protector to best available target by marginal/time (excluding its source)
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

        # Final: set all assignments explicitly
        for d in drones:
            g = assigned[d]
            if g is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, g)