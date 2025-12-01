from math import hypot
from typing import Dict, List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Preserve all current targetings (comp.target_id) initially.
        - Ensure the highest-threat field is fully protected:
            - If it's already fully protected, keep as is.
            - Otherwise, add untargeted drones first; if still short, reassign drones from
              the least valuable currently-protected fields (lowest threat_per_drone).
        - Greedily try to fully protect additional fields by benefit (threat / drones_needed),
          using closest untargeted drones.
        - Assign any remaining untargeted drones one-by-one by marginal benefit that includes arrival time.
        - Any remaining unassigned drones -> "idle".
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

        # indexable components
        n = len(components)
        indices = list(range(n))

        # threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # nothing to protect
            target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else "idle")
            for comp in components:
                environment.assign_group(comp, target)
            return

        # choose top field (highest threat; tie by id)
        threatened.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top_field = threatened[0]
        top_id = top_field.id

        # precompute centers and required counts
        centers = {f.id: center_of(f) for f in threatened}
        def required_for(f):
            try:
                return max(0, int(f.drones_for_full_protection))
            except Exception:
                return 0
        required = {f.id: required_for(f) for f in threatened}

        # map current targeting: field_id -> list of drone indices
        current_targeting: Dict[str, List[int]] = {}
        for i, comp in enumerate(components):
            tid = comp.target_id
            if tid is not None:
                current_targeting.setdefault(tid, []).append(i)

        # Assigned mapping (we'll fill and then call environment.assign_group)
        assigned: Dict[int, str] = {}

        # 1) Preserve all current targetings (keep comp.target_id assignments)
        for fid, lst in current_targeting.items():
            for idx in lst:
                assigned[idx] = fid

        # 2) Ensure top field fully protected.
        top_assigned_indices = [i for i, fid in assigned.items() if fid == top_id]
        top_assigned_count = len(top_assigned_indices)
        top_required = required.get(top_id, 0)
        if top_assigned_count < top_required:
            need = top_required - top_assigned_count
            # Prefer untargeted drones first: those with comp.target_id is None
            untargeted = [i for i in indices if components[i].target_id is None and i not in assigned]
            # sort untargeted by distance to top center
            untargeted.sort(key=lambda i: distance_to(centers[top_id], i))
            take_from_untargeted = untargeted[:need]
            for i in take_from_untargeted:
                assigned[i] = top_id
            need -= len(take_from_untargeted)

            if need > 0:
                # If still need, select assigned drones from other fields to reassign.
                # Choose donors from currently assigned drones on other fields ranked by least-value:
                # value per drone = field.threat_level / max(1, required[field])
                donor_candidates = []
                for f in threatened:
                    fid = f.id
                    if fid == top_id:
                        continue
                    # list of drones currently assigned to this field
                    donors = [i for i, afid in assigned.items() if afid == fid]
                    if not donors:
                        continue
                    # compute field value per drone (lower means less valuable to lose)
                    denom = max(1, required.get(fid, 0))
                    val_per_drone = f.threat_level / denom if denom > 0 else 0.0
                    # For tie-breaker use distance of each donor to its current field center (prefer reassigning those far from their field)
                    for d in donors:
                        dist_from_own = distance_to(centers[fid], d)
                        donor_candidates.append((val_per_drone, dist_from_own, fid, d))
                # Sort donors: first by increasing val_per_drone (we want to pick least valuable fields),
                # then prefer donors that are far from their own field (increasing negative priority -> larger distance preferred)
                donor_candidates.sort(key=lambda t: (t[0], -t[1], str(t[2]), t[3]))
                # select donors to meet the need
                for entry in donor_candidates[:need]:
                    _, _, donor_field, donor_idx = entry
                    # remove donor assignment and reassign to top
                    assigned[donor_idx] = top_id
                    need -= 1
                    if need <= 0:
                        break
            # After possible reassignments, top should be as filled as possible.
        # if top already had >= required, we left them as is (spec says keep them)

        # 3) Greedy full-protection for other fields using untargeted drones (we preserved current targeters)
        # available untargeted drones are those not in assigned
        available = [i for i in indices if i not in assigned]
        # We'll try to fully protect other fields, prioritized by benefit = threat / max(1, (required - assigned_count))
        # where assigned_count is current assigned (preserved)
        other_fields = [f for f in threatened if f.id != top_id]
        # compute current assigned counts
        assigned_count = {}
        for f in threatened:
            fid = f.id
            assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)

        # Candidate fields needing additional drones
        fields_need = []
        for f in other_fields:
            fid = f.id
            need = max(0, required.get(fid, 0) - assigned_count.get(fid, 0))
            if need > 0:
                # benefit per drone ignoring travel = threat / need
                benefit = f.threat_level / float(need) if need > 0 else 0.0
                fields_need.append((benefit, f))
        # Sort by benefit desc (tie by id)
        fields_need.sort(key=lambda t: (-t[0], str(t[1].id)))

        # For each field in that order, try to assign closest available drones to fully protect it
        for benefit, f in fields_need:
            fid = f.id
            need = max(0, required.get(fid, 0) - assigned_count.get(fid, 0))
            if need <= 0:
                continue
            if not available:
                break
            # choose closest available drones to this field
            available.sort(key=lambda i: distance_to(centers[fid], i))
            take = min(need, len(available))
            for i in available[:take]:
                assigned[i] = fid
                assigned_count[fid] = assigned_count.get(fid, 0) + 1
            # update available
            available = [i for i in available if i not in assigned]

        # 4) Assign remaining untargeted drones one-by-one by marginal benefit
        # marginal value of assigning drone i to field f:
        #   marginal = (f.threat_level / max(1, required[f])) / (1 + arrival_time)
        # also reduce attractiveness if field is already fully protected
        available = [i for i in indices if i not in assigned]
        if available:
            # recompute assigned counts
            assigned_count = {}
            for f in threatened:
                fid = f.id
                assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)

            # iterate until no available drones or no positive marginal
            while available:
                best_val = 0.0
                best_pair = None  # (drone_idx, field_id)
                for i in available:
                    for f in threatened:
                        fid = f.id
                        req = max(1, required.get(fid, 0))
                        arrival = distance_to(centers[fid], i) / DRONE_SPEED
                        base = f.threat_level / float(req)
                        # if already fully protected, discourage additional assignment strongly
                        if assigned_count.get(fid, 0) >= required.get(fid, 0):
                            base *= 0.2
                        val = base / (1.0 + arrival)
                        # deterministic tie-breaker by (drone idx, field id)
                        if val > best_val or (abs(val - best_val) < 1e-12 and best_pair is not None and (i < best_pair[0] or (i == best_pair[0] and str(fid) < str(best_pair[1])))):
                            best_val = val
                            best_pair = (i, fid)
                if best_pair is None or best_val <= 0.0:
                    break
                # assign best
                di, fid = best_pair
                assigned[di] = fid
                assigned_count[fid] = assigned_count.get(fid, 0) + 1
                available = [i for i in available if i != di]

        # 5) Any remaining unassigned -> idle
        # (At this point, available = [i not in assigned])
        available = [i for i in indices if i not in assigned]

        # 6) Apply assignments via environment.assign_group
        protecting_prefix = "protecting "
        protecting_groups = {g for g in group_ids if g.startswith(protecting_prefix)}
        for i, comp in enumerate(components):
            if i in assigned:
                fid = assigned[i]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    # fallback: pick any protecting group if exists, else idle, else first group
                    if protecting_groups:
                        environment.assign_group(comp, next(iter(protecting_groups)))
                    elif idle_group in group_ids:
                        environment.assign_group(comp, idle_group)
                    else:
                        environment.assign_group(comp, group_ids[0] if group_ids else "idle")
            else:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0] if group_ids else "idle")