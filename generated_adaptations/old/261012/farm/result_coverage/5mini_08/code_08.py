from math import hypot
from typing import Dict, List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Fully protect the highest-threat field using the closest drones (may reassign drones from other fields).
        - Preserve remaining current targetings as initial assignments for other fields.
        - For remaining free drones, iteratively assign the drone that yields the highest marginal benefit
          (threat/required divided by 1+arrival_time) to a field that is not yet fully protected.
        - Any leftover drones -> idle.
        """
        DRONE_SPEED = 2.0

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to(point, comp_idx):
            c = components[comp_idx]
            dx = c.location.x - point[0]
            dy = c.location.y - point[1]
            return hypot(dx, dy)

        idle_group = "idle"
        protecting_prefix = "protecting "

        # Index components for deterministic processing
        n = len(components)
        indices = list(range(n))

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all idle
        if not threatened:
            target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else "idle")
            for comp in components:
                environment.assign_group(comp, target)
            return

        # Choose top field (highest threat, tie-break by id)
        threatened.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top_field = threatened[0]
        top_id = top_field.id

        # Precompute centers and required numbers
        centers = {f.id: center_of(f) for f in threatened}
        def required_for(f):
            try:
                return max(0, int(f.drones_for_full_protection))
            except Exception:
                return 0
        required = {f.id: required_for(f) for f in threatened}

        # Map current targeting: which drone indices currently target which field id
        current_targeting: Dict[str, List[int]] = {}
        for i, comp in enumerate(components):
            tid = comp.target_id
            if tid is not None:
                current_targeting.setdefault(tid, []).append(i)

        # Final assignment map: comp_idx -> field_id (protecting that field)
        assigned: Dict[int, str] = {}

        # STEP 1: Ensure top field is fully protected.
        already_top = list(current_targeting.get(top_id, []))
        # Assign those that already target top
        for idx in already_top:
            assigned[idx] = top_id

        top_needed = max(0, required.get(top_id, 0) - len(already_top))
        if top_needed > 0:
            # Select closest drones among all drones that are not already assigned to top
            candidates = [i for i in indices if i not in assigned]
            candidates.sort(key=lambda i: distance_to(centers[top_id], i))
            for i in candidates[:top_needed]:
                assigned[i] = top_id

        # STEP 2: Preserve current targetings of other fields (they remain assigned initially)
        for f in threatened:
            fid = f.id
            if fid == top_id:
                continue
            for idx in current_targeting.get(fid, []):
                # If this drone was moved to top in step 1, skip; otherwise preserve
                if idx not in assigned:
                    assigned[idx] = fid

        # Available drones are those not yet assigned
        available = [i for i in indices if i not in assigned]

        # Precompute a mapping from field id to current assigned count
        assigned_count: Dict[str, int] = {}
        for f in threatened:
            fid = f.id
            assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)

        # STEP 3: Greedy per-drone marginal assignment
        # Marginal benefit for assigning one drone j to field f:
        # if assigned_count[f] >= required[f]: marginal = 0
        # else marginal = (f.threat_level / max(1, required[f])) / (1 + arrival_time_jf)
        # where arrival_time_jf = distance(drone_j, center_f) / DRONE_SPEED
        while available:
            best_val = 0.0
            best_pair = None  # (drone_idx, field_id, arrival_time)
            # Evaluate each available drone and each field
            for i in available:
                for f in threatened:
                    fid = f.id
                    req = required.get(fid, 0)
                    if req <= 0:
                        continue
                    if assigned_count.get(fid, 0) >= req:
                        # already fully protected
                        continue
                    arrival = distance_to(centers[fid], i) / DRONE_SPEED
                    # marginal protection fraction by adding one drone = 1/req (unless assigned_count+1 > req, but we only add one at a time)
                    marginal_fraction = 1.0 / req
                    # benefit scales with threat and is reduced by arrival time
                    val = (f.threat_level * marginal_fraction) / (1.0 + arrival)
                    # deterministic tie-break: prefer smaller index and smaller field id
                    if val > best_val or (abs(val - best_val) < 1e-12 and best_pair is not None and ( (i < best_pair[0]) or (i == best_pair[0] and str(fid) < str(best_pair[1])) )):
                        best_val = val
                        best_pair = (i, fid, arrival)
                    elif val > 0 and best_pair is None:
                        best_pair = (i, fid, arrival)
                        best_val = val
            if best_pair is None or best_val <= 0.0:
                break
            # Assign best drone to best field
            drone_idx, field_id, _ = best_pair
            assigned[drone_idx] = field_id
            assigned_count[field_id] = assigned_count.get(field_id, 0) + 1
            # remove from available
            available = [i for i in available if i != drone_idx]

        # STEP 4: Any remaining available drones -> idle
        for i in available:
            # leave unassigned in our map to be put idle below
            pass

        # STEP 5: Apply assignments via environment.assign_group for every component
        # Ensure group name exists else fallback to idle or any protecting group
        protecting_groups = {g for g in group_ids if g.startswith(protecting_prefix)}
        for idx, comp in enumerate(components):
            if idx in assigned:
                fid = assigned[idx]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    # fallback: any protecting group if exists, else idle, else first group_id
                    if protecting_groups:
                        environment.assign_group(comp, next(iter(protecting_groups)))
                    elif idle_group in group_ids:
                        environment.assign_group(comp, idle_group)
                    else:
                        environment.assign_group(comp, group_ids[0] if group_ids else "idle")
            else:
                # assign idle
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0] if group_ids else "idle")