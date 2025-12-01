from typing import List, Dict, Set
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Strategy:
        - Fully protect the highest-threat field first (closest drones, prefer committed/idle/moving, only steal protecting extras).
        - Then assign remaining drones one-by-one to the field that gives the highest marginal benefit
          (benefit considers field threat, how close the field is to full protection, and travel distance).
        - Do not steal protecting drones (except extras used to secure the top field).
        - Explicitly assign every drone to exactly one group.
        """

        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(ax, ay, bx, by):
            return math.hypot(ax - bx, ay - by)

        # Group fallback
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Precompute centers and field lookup
        centers = {f.id: center(f) for f in threatened}
        field_by_id = {f.id: f for f in threatened}

        # Compute farm diagonal for normalizing distances
        xs, ys = [], []
        for f in environment.fields:
            xs.extend([f.left, f.right]); ys.extend([f.top, f.bottom])
        for d in components:
            xs.append(d.location.x); ys.append(d.location.y)
        if xs and ys:
            farm_diag = max(1.0, dist(min(xs), min(ys), max(xs), max(ys)))
        else:
            farm_diag = 1.0

        # Partition drones by state/target
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

        # Deterministic ordering keys
        def drone_key(d):
            return (d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or "")

        def dist_to_field(d, fid):
            cx, cy = centers[fid]
            return dist(d.location.x, d.location.y, cx, cy)

        # Choose top field (highest threat, deterministic tie break)
        top_field = max(threatened, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # if protecting group missing, idle all
            for d in all_drones:
                environment.assign_group(d, fallback_group)
            return
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))

        # --- Secure top field ---
        selected_top: List = []
        selected_top_set: Set = set()

        # (1) committed to top: protecting then moving
        committed_top = []
        committed_top.extend(sorted(protecting_by_field.get(top_id, []), key=drone_key))
        committed_top.extend(sorted(moving_by_field.get(top_id, []), key=drone_key))
        for d in committed_top:
            if len(selected_top) >= top_required:
                break
            selected_top.append(d)
            selected_top_set.add(d)

        # (2) idle drones nearest
        if len(selected_top) < top_required:
            idle_candidates = [d for d in idle_drones if d not in selected_top_set]
            idle_candidates.sort(key=lambda d: (dist_to_field(d, top_id), drone_key(d)))
            for d in idle_candidates:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (3) moving_to_field (other targets) nearest
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

        # (4) protecting extras from other fields (protectors beyond required)
        if len(selected_top) < top_required:
            extras = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                req = int(getattr(field_by_id.get(fid, None), "drones_for_full_protection", 0))
                extra = max(0, len(prots) - req)
                if extra <= 0:
                    continue
                for d in sorted(prots, key=lambda d: (dist_to_field(d, top_id), drone_key(d))):
                    extras.append((getattr(field_by_id.get(fid), "threat_level", 0), dist_to_field(d, top_id), fid, d))
            # prefer smallest-threat donor fields first (less harmful)
            extras.sort(key=lambda t: (t[0], t[1], drone_key(t[3])))
            for _, _, _, d in extras:
                if len(selected_top) >= top_required:
                    break
                if d in selected_top_set:
                    continue
                selected_top.append(d)
                selected_top_set.add(d)

        # (5) last resort: steal protectors from lowest-threat fields (closest first)
        if len(selected_top) < top_required:
            protect_candidates = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                field_threat = getattr(field_by_id.get(fid, None), "threat_level", 0)
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

        # --- Build initial assignment mapping, default idle ---
        drone_to_group: Dict[object, str] = {}
        for d in all_drones:
            drone_to_group[d] = fallback_group

        # Assign protectors to their groups unless stolen for top
        for fid, prots in protecting_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in prots:
                if d in selected_top_set:
                    continue
                drone_to_group[d] = grp

        # Assign moving_to_field drones to their target group if not stolen
        for fid, movs in moving_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in movs:
                if d in selected_top_set:
                    continue
                # don't overwrite existing protectors
                if drone_to_group.get(d, fallback_group) == fallback_group:
                    drone_to_group[d] = grp

        # Assign top-group for selected_top drones
        for d in selected_top:
            drone_to_group[d] = top_group

        # --- Prepare available drone pool: do not include protecting drones that we left in place ---
        assigned_set = set(d for d, g in drone_to_group.items() if g != fallback_group)
        available = [d for d in all_drones if d not in assigned_set]

        # Compute current assigned counts per field (from drone_to_group)
        assigned_counts: Dict[str, int] = {}
        for f in threatened:
            fid = f.id
            assigned_counts[fid] = sum(1 for d, g in drone_to_group.items() if g == f"protecting {fid}")

        # Ensure top field assigned count equals selected_top length
        assigned_counts[top_id] = len([d for d in selected_top if drone_to_group.get(d) == top_group])

        # --- Stage 2: greedily assign available drones one-by-one by marginal benefit ---
        # Marginal benefit for assigning drone d to field fid:
        # benefit = threat * remaining_fraction / (1 + normalized_distance)
        # where remaining_fraction = (required - assigned_count) / required
        def marginal_benefit(d, fid):
            info = field_by_id[fid]
            req = int(getattr(info, "drones_for_full_protection", 0))
            if req <= 0:
                return 0.0
            already = assigned_counts.get(fid, 0)
            if already >= req:
                return 0.0
            remaining = req - already
            rem_frac = remaining / req
            distance_norm = dist_to_field(d, fid) / farm_diag
            # small bonus if already targeting that field
            bonus = 1.2 if getattr(d, "target_id", None) == fid else 1.0
            # compute score
            score = getattr(info, "threat_level", 0) * rem_frac * bonus / (1.0 + distance_norm)
            return score

        # To prefer finishing near-complete fields, we'll let rem_frac reflect how close field is to full
        # Assign drones until available exhausted or no beneficial assignment
        # Deterministic ordering of available drones
        available.sort(key=lambda d: (d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or ""))

        while available:
            best_drone = None
            best_fid = None
            best_score = 0.0
            # For each drone, find its best field and score
            for d in available:
                best_field_for_d = None
                best_score_for_d = 0.0
                for f in threatened:
                    fid = f.id
                    # skip top if it's already fully assigned
                    if assigned_counts.get(fid, 0) >= int(getattr(field_by_id[fid], "drones_for_full_protection", 0)):
                        continue
                    sc = marginal_benefit(d, fid)
                    if sc > best_score_for_d:
                        best_score_for_d = sc
                        best_field_for_d = fid
                # choose drone with maximal best_score_for_d
                if best_score_for_d > best_score:
                    best_score = best_score_for_d
                    best_drone = d
                    best_fid = best_field_for_d
            # If no positive score found, stop
            if best_drone is None or best_score <= 1e-8:
                break
            # Assign best_drone to best_fid
            drone_to_group[best_drone] = f"protecting {best_fid}"
            assigned_counts[best_fid] = assigned_counts.get(best_fid, 0) + 1
            # remove from available
            available.remove(best_drone)

        # Any remaining available drones remain idle (already set)

        # Final: explicitly assign every drone
        for d in all_drones:
            grp = drone_to_group.get(d, fallback_group)
            # validate group exists (protecting groups exist only for fields with threat>0)
            if grp.startswith("protecting "):
                # ensure group present; otherwise fallback
                if grp not in group_ids:
                    grp = fallback_group
            environment.assign_group(d, grp)