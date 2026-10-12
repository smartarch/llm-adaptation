from typing import List, Dict, Set
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        - Fully protect the highest-threat field first (committed first, then idle, movers, extras, last-resort protectors).
        - Then greedily fully protect additional fields by maximizing threat / (k * (1 + avg_arrival_time_of_k_closest)).
        - Remaining drones -> idle.
        """
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def euclid(ax, ay, bx, by):
            return math.hypot(ax - bx, ay - by)

        SPEED = 2.0  # drone speed
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Fields with threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        # Useful helpers
        def dist_to_field(drone, fid):
            cx, cy = centers[fid]
            return euclid(drone.location.x, drone.location.y, cx, cy)

        # Partition drones
        protecting_by_field: Dict[str, List] = {}
        moving_by_field: Dict[str, List] = {}
        idle_drones: List = []
        all_drones = list(components)

        for d in all_drones:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st == "protecting" and tid is not None:
                protecting_by_field.setdefault(tid, []).append(d)
            elif st == "moving_to_field" and tid is not None:
                moving_by_field.setdefault(tid, []).append(d)
            else:
                idle_drones.append(d)

        # Deterministic key for tie-breaking
        def drone_key(d):
            return (d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or "")

        # Determine top field by threat (tie-break by id)
        top_field = max(fields, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # fallback: can't protect by name, idle all
            for comp in all_drones:
                environment.assign_group(comp, fallback_group)
            return
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))

        # --- Select drones for top field ---
        selected_top: List = []
        selected_top_set: Set = set()

        # 1) committed to top: protecting then moving (deterministic)
        committed_top = []
        committed_top.extend(sorted(protecting_by_field.get(top_id, []), key=drone_key))
        committed_top.extend(sorted(moving_by_field.get(top_id, []), key=drone_key))
        for d in committed_top:
            if len(selected_top) >= top_required:
                break
            selected_top.append(d)
            selected_top_set.add(d)

        # 2) idle drones closest
        if len(selected_top) < top_required and idle_drones:
            idle_candidates = [d for d in idle_drones if d not in selected_top_set]
            idle_candidates.sort(key=lambda d: (dist_to_field(d, top_id), drone_key(d)))
            for d in idle_candidates:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # 3) moving to other fields, closest
        if len(selected_top) < top_required:
            movers = []
            for fid, movs in moving_by_field.items():
                if fid == top_id:
                    continue
                for d in movs:
                    if d not in selected_top_set:
                        movers.append(d)
            movers.sort(key=lambda d: (dist_to_field(d, top_id), drone_key(d)))
            for d in movers:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # 4) protecting-extras from other fields (protectors beyond required), prefer donors with lower threat and closeness
        if len(selected_top) < top_required:
            extra_list = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                required = int(getattr(fields_by_id.get(fid, None), "drones_for_full_protection", 0))
                extra = max(0, len(prots) - required)
                if extra <= 0:
                    continue
                for d in sorted(prots, key=lambda d: (dist_to_field(d, top_id), drone_key(d))):
                    extra_list.append((getattr(fields_by_id[fid], "threat_level", 0), dist_to_field(d, top_id), fid, d))
            extra_list.sort(key=lambda t: (t[0], t[1], drone_key(t[3])))
            for _, _, _, d in extra_list:
                if len(selected_top) >= top_required:
                    break
                if d in selected_top_set:
                    continue
                selected_top.append(d)
                selected_top_set.add(d)

        # 5) last resort: steal protectors from lowest-threat fields, closest first
        if len(selected_top) < top_required:
            protect_candidates = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                field_threat = getattr(fields_by_id.get(fid, None), "threat_level", 0)
                for d in prots:
                    if d in selected_top_set:
                        continue
                    protect_candidates.append((field_threat, dist_to_field(d, top_id), fid, d))
            protect_candidates.sort(key=lambda t: (t[0], t[1], drone_key(t[3])))
            for _, _, _, d in protect_candidates:
                if len(selected_top) >= top_required:
                    break
                if d in selected_top_set:
                    continue
                selected_top.append(d)
                selected_top_set.add(d)

        # --- Build initial assignment mapping (default idle) and preserve non-stolen protectors/movers where possible ---
        drone_to_group: Dict[object, str] = {}
        for d in all_drones:
            drone_to_group[d] = fallback_group

        # Assign protecting drones to their groups unless they were stolen for top
        for fid, prots in protecting_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in prots:
                if d in selected_top_set:
                    continue
                drone_to_group[d] = grp

        # Assign moving_to_field drones to their target groups unless stolen
        for fid, movs in moving_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in movs:
                if d in selected_top_set:
                    continue
                # do not overwrite protectors
                if drone_to_group.get(d, fallback_group) == fallback_group:
                    drone_to_group[d] = grp

        # Assign top-selected drones to top_group
        for d in selected_top:
            drone_to_group[d] = top_group

        # Build available drones pool (those currently idle in mapping)
        assigned_set = set(d for d, g in drone_to_group.items() if g != fallback_group)
        available = [d for d in all_drones if d not in assigned_set]

        # --- Greedy selection for additional fields: score = threat / (k * (1 + avg_arrival_time)) ---
        # Helper: compute travel time
        def travel_time(d, fid):
            return dist_to_field(d, fid) / SPEED

        # Iterate selecting best field to fully protect next
        remaining_fields = [f for f in fields if f.id != top_id]
        # Deterministic order tie-breakers included when equal scores
        while True:
            best_field = None
            best_score = 0.0
            best_choice: List = []
            for f in remaining_fields:
                fid = f.id
                grp = f"protecting {fid}"
                if grp not in group_ids:
                    continue
                required = int(getattr(f, "drones_for_full_protection", 0))
                # count currently assigned to this field (protectors/movers we kept)
                currently_assigned = [d for d, g in drone_to_group.items() if g == grp]
                need = max(0, required - len(currently_assigned))
                if need <= 0:
                    # already satisfied
                    continue
                # if not enough available drones to fill need, skip
                if len(available) < need:
                    continue
                # pick need drones among available with smallest travel_time
                avail_sorted = sorted(available, key=lambda d: (travel_time(d, fid), drone_key(d)))
                chosen = avail_sorted[:need]
                arrival_times = [travel_time(d, fid) for d in chosen]
                avg_arrival = sum(arrival_times) / len(arrival_times) if arrival_times else 0.0
                # score: threat / (k * (1 + avg_arrival)), include small eps to avoid division by zero
                score = (getattr(f, "threat_level", 0) or 0.0) / (need * (1.0 + avg_arrival + 1e-9))
                # tie-break: prefer higher threat or smaller avg_arrival
                if score > best_score or (abs(score - best_score) < 1e-12 and ((f.threat_level, -avg_arrival, fid) > (best_field.threat_level, - (sum(travel_time(d, best_field.id) for d in best_choice) / len(best_choice) if best_choice else 0.0), best_field.id) if best_field else True)):
                    best_score = score
                    best_field = f
                    best_choice = chosen
            if best_field is None:
                break
            # assign chosen drones to best_field
            grp = f"protecting {best_field.id}"
            for d in best_choice:
                drone_to_group[d] = grp
                if d in available:
                    available.remove(d)
            # remove field from consideration
            remaining_fields = [f for f in remaining_fields if f.id != best_field.id]

        # Any drones left in available remain or become idle (already default)
        # Ensure every drone is explicitly assigned
        for d in all_drones:
            grp = drone_to_group.get(d, fallback_group)
            # validate group exists; fallback if not
            if grp not in group_ids:
                grp = fallback_group
            environment.assign_group(d, grp)