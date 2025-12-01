from typing import List, Dict, Set, Tuple
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Improved strategy with partial-support allocation:

        1. Identify fields with threat_level > 0. If none, assign all drones to idle.
        2. For the highest-threat field:
           - If already fully protected (committed >= required), keep those drones.
           - Otherwise, add closest drones preferring idle and moving drones, avoid stealing protecting drones unless necessary.
        3. Greedily fully protect other fields as possible without breaking current protections.
        4. For any leftover drones, assign them one-by-one to the field where each drone gives the highest marginal benefit,
           considering field threat, remaining fraction to full protection, and travel time (so close drones are used).
        5. Assign any drones not providing positive marginal benefit to "idle".
        """
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(a_x, a_y, b_x, b_y):
            return math.hypot(a_x - b_x, a_y - b_y)

        SPEED = 2.0  # drone speed given in problem
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Collect threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Precompute centers
        centers = {f.id: center(f) for f in threatened}

        # Compute farm scale to normalize distances (diagonal)
        xs, ys = [], []
        for f in environment.fields:
            xs.extend([f.left, f.right]); ys.extend([f.top, f.bottom])
        for d in components:
            xs.append(d.location.x); ys.append(d.location.y)
        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            diag = dist(min_x, min_y, max_x, max_y)
            max_dist = max(diag, 1.0)
        else:
            max_dist = 1.0

        # Partition drones by state/target
        protecting_by_field: Dict[str, List] = {}
        moving_by_field: Dict[str, List] = {}
        idle_drones: List = []

        all_comps = list(components)
        for comp in all_comps:
            st = getattr(comp, "state", "")
            tid = getattr(comp, "target_id", None)
            if st == "protecting" and tid is not None:
                protecting_by_field.setdefault(tid, []).append(comp)
            elif st == "moving_to_field" and tid is not None:
                moving_by_field.setdefault(tid, []).append(comp)
            else:
                idle_drones.append(comp)

        # Helper: distance from drone to field center
        def dist_to_field_drone(drone, fid):
            cx, cy = centers[fid]
            return dist(drone.location.x, drone.location.y, cx, cy)

        # Determine top field (highest threat, tie break by id)
        top_field = max(threatened, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # fallback
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Field requirements and quick info structure
        field_info = {}
        for f in threatened:
            fid = f.id
            req = int(getattr(f, "drones_for_full_protection", 0))
            protecting = list(protecting_by_field.get(fid, []))
            moving = list(moving_by_field.get(fid, []))
            committed = protecting + moving
            field_info[fid] = {
                "field": f,
                "required": req,
                "protecting": protecting,
                "moving": moving,
                "committed": list(committed),
                "threat": getattr(f, "threat_level", 0),
            }

        # ---- Stage 1: secure top field ----
        top_required = field_info[top_id]["required"]
        top_committed = list(field_info[top_id]["committed"])
        selected_for_top: List = []

        # If already fully protected, keep committed drones there
        if len(top_committed) >= top_required:
            # Keep those protecting/moving to the top
            selected_for_top = top_committed[:top_required]  # keep first required if more than needed
        else:
            # Start with committed (protecting + moving to top)
            selected_for_top = list(top_committed)
            needed = max(0, top_required - len(selected_for_top))

            # Candidates in order: idle drones, moving drones going elsewhere, then protecting extras from other fields, then protecting others as last resort
            # Build pools
            idle_pool = list(idle_drones)
            movers_elsewhere = [d for fid, movs in moving_by_field.items() for d in movs if fid != top_id]
            # protecting extras (fields with more protecting than required)
            protecting_extras = []
            protecting_other = []
            for fid, info in field_info.items():
                if fid == top_id:
                    continue
                prot = info["protecting"]
                if not prot:
                    continue
                extra = max(0, len(prot) - info["required"])
                if extra > 0:
                    # include extras first
                    protecting_extras.extend(prot)
                else:
                    protecting_other.extend(prot)

            # Candidate pool preserving order: idle_pool, movers_elsewhere, protecting_extras, protecting_other
            candidate_pool = []
            candidate_pool.extend(idle_pool)
            candidate_pool.extend(movers_elsewhere)
            candidate_pool.extend(protecting_extras)
            candidate_pool.extend(protecting_other)

            # Remove duplicates while preserving order
            seen = set()
            uniq_candidates = []
            for d in candidate_pool:
                if d not in seen:
                    uniq_candidates.append(d); seen.add(d)

            # Sort candidates by distance to top (prefer close)
            uniq_candidates.sort(key=lambda d: (dist_to_field_drone(d, top_id), getattr(d, "target_id", None) or "", getattr(d, "state", "")))

            # Pick needed drones
            to_take = uniq_candidates[:needed]
            for d in to_take:
                selected_for_top.append(d)

        # Mark selected_for_top as assigned
        assigned: Dict[str, List] = {}
        assigned[top_id] = list(selected_for_top)
        assigned_set = set(assigned[top_id])

        # ---- Stage 2: attempt to fully protect other fields (greedy by benefit/cost) without breaking protecting drones ----
        # Build available drone pool: any drone not already assigned for top, but protectors for other fields are reserved (we keep them where they are)
        available = [d for d in all_comps if d not in assigned_set and not any(d in field_info[fid]["protecting"] for fid in field_info if fid != top_id)]
        # Note: this preserves protecting drones for other fields; we may use movers and idle
        # Candidate fields excluding top
        other_fields = [f for f in threatened if f.id != top_id]
        # Sort by threat descending for determinism
        other_fields.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)

        # Helper: compute effective per-drone cost for selecting drone d to field fid
        # We penalize long travel and stealing moving drones a bit; protecting drones shouldn't be in available pool here
        def effective_cost_for_full(d, fid):
            # base cost proportional to normalized distance
            travel = dist_to_field_drone(d, fid) / max_dist
            base = 1.0 + travel
            # small bonus if already targeting that field
            if getattr(d, "target_id", None) == fid:
                return 0.15  # very cheap if already heading there
            # minor penalty if moving_to_field to different target
            if getattr(d, "state", "") == "moving_to_field":
                return base + 0.4
            return base

        # For each other field, try to pick cheapest k drones from available pool to fully protect
        for f in other_fields:
            fid = f.id
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            # Count already committed (protecting+moving to this field) among drones we are allowed to keep
            committed_here = [d for d in all_comps if getattr(d, "target_id", None) == fid and getattr(d, "state", "") in ("protecting", "moving_to_field")]
            # But we reserved protecting drones in earlier available filter; include commuting moving ones if they are not assigned away
            current_selected = list(committed_here)
            # How many still needed
            needed = max(0, req - len(current_selected))
            if needed <= 0:
                # keep committed; assign group info later
                assigned[fid] = current_selected
                continue
            # If not enough available drones to fill needed, skip (we don't steal protecting drones here)
            if len(available) < needed:
                continue
            # Compute cheapest selection of needed drones
            candidates = sorted(available, key=lambda d: (effective_cost_for_full(d, fid), getattr(d, "target_id", None) or "", getattr(d, "state", "")))
            chosen = candidates[:needed]
            # Assign them
            assigned[fid] = current_selected + chosen
            # Remove chosen from available
            for d in chosen:
                if d in available:
                    available.remove(d)

        # ---- Stage 3: use leftover drones for partial support (per-drone greedy) ----
        leftover = [d for d in all_comps if d not in set().union(*[set(v) for v in assigned.values()])]

        # Build current assigned counts per field
        assigned_counts: Dict[str, int] = {}
        for fid in assigned:
            assigned_counts[fid] = len(assigned[fid])
        for f in threatened:
            if f.id not in assigned_counts:
                assigned_counts[f.id] = 0

        # Per-drone assignment: for each leftover drone, compute marginal score for each field:
        # score = threat * remaining_fraction / (1 + travel_time_norm)
        # where remaining_fraction = max(0, (required - assigned_count)/required)
        # travel_time_norm = (distance / SPEED) normalized by max_dist so closer better
        # Choose field with highest score > threshold, else assign idle
        def marginal_score(d, fid):
            info = field_info[fid]
            req = info["required"]
            if req <= 0:
                return 0.0
            remaining = max(0, req - assigned_counts.get(fid, 0))
            if remaining <= 0:
                # field is already fully protected
                return 0.0
            # normalized travel time penalty
            travel = dist_to_field_drone(d, fid) / max_dist
            travel_time = (dist_to_field_drone(d, fid) / SPEED)  # in time units; we combine normalized travel and time indirectly
            # remaining fraction
            rem_frac = remaining / req
            # small bonus if already committed
            bonus = 1.2 if getattr(d, "target_id", None) == fid else 1.0
            # score formulation
            score = info["threat"] * rem_frac * bonus / (1.0 + travel + 0.5 * travel_time)
            return score

        # For determinism sort leftover by id-like characteristics (state + target + coordinates)
        leftover.sort(key=lambda d: (getattr(d, "state", ""), getattr(d, "target_id", "") or "", d.location.x, d.location.y))

        for d in leftover:
            best_fid = None
            best_score = 0.0
            # consider only fields that are not fully protected yet
            for f in threatened:
                fid = f.id
                if assigned_counts.get(fid, 0) >= field_info[fid]["required"]:
                    continue
                sc = marginal_score(d, fid)
                # tie-break by threat then id
                if sc > best_score or (abs(sc - best_score) < 1e-12 and (field_info[fid]["threat"], fid) > (field_info[best_fid]["threat"], best_fid) if best_fid else True):
                    best_score = sc
                    best_fid = fid
            # threshold: only assign if best_score is meaningful (> 0)
            if best_fid is not None and best_score > 1e-6:
                # assign this drone to best_fid (partial support)
                assigned.setdefault(best_fid, [])
                assigned[best_fid].append(d)
                assigned_counts[best_fid] = assigned_counts.get(best_fid, 0) + 1
            else:
                # leave idle (handled later)
                pass

        # ---- Final: call environment.assign_group for every component ----
        drone_to_group: Dict[object, str] = {}
        for fid, drones in assigned.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in drones:
                drone_to_group[d] = grp

        for comp in all_comps:
            grp = drone_to_group.get(comp, fallback_group)
            environment.assign_group(comp, grp)