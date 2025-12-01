from math import hypot
from itertools import combinations
from typing import Dict, List, Set, Tuple
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Subset-selection + careful donor selection strategy.

        1. Consider all subsets of threatened fields that include the top-threat field and whose
           total required drones <= total drones. Choose the subset maximizing total threat_level
           (tie-break by smaller total required).
        2. For chosen subset S, allocate drones:
           - preserve drones already targeting fields in S,
           - assign untargeted drones (closest first),
           - if still needed, pick donor drones from fields outside S by minimal cost_metric:
             cost_metric = (loss_if_removed) / (1 / (1 + arrival_time_to_target))
               where loss_if_removed approximates the field's threat contribution lost (threat / required).
        3. With remaining drones, do single-drone marginal assignments to other fields by
           benefit = (field.threat / required) / (1 + arrival_time).
        4. Assign all unassigned drones to "idle".
        """
        DRONE_SPEED = 2.0

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(drone_idx: int, point: Tuple[float, float]) -> float:
            d = components[drone_idx]
            dx = d.location.x - point[0]
            dy = d.location.y - point[1]
            return hypot(dx, dy)

        idle_group = "idle"
        protecting_prefix = "protecting "

        # Indexable components
        n = len(components)
        indices = list(range(n))

        # Threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle everyone
        if not threatened:
            target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else "idle")
            for comp in components:
                environment.assign_group(comp, target)
            return

        # Top field: highest threat (tie-break by id)
        threatened.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top_field = threatened[0]
        top_id = top_field.id

        # Precompute centers and required counts
        centers = {f.id: center_of(f) for f in threatened}
        def required_for(f):
            try:
                return max(0, int(f.drones_for_full_protection))
            except Exception:
                return 0
        required = {f.id: required_for(f) for f in threatened}

        # Map current targetings
        current_targeting: Dict[str, List[int]] = {}
        for i, comp in enumerate(components):
            tid = comp.target_id
            if tid is not None:
                current_targeting.setdefault(tid, []).append(i)

        # Total drones available
        total_drones = n

        # Build list of field ids for subset enumeration
        field_list = threatened  # already sorted
        m = len(field_list)

        # Enumerate feasible subsets containing top_field
        best_subset: Set[str] = set([top_id])
        best_value = -1.0
        best_required_sum = None

        # To limit combinatorial explosion we can enumerate subsets up to a reasonable size,
        # but we'll enumerate all (fields count typically small).
        ids = [f.id for f in field_list]
        id_to_field = {f.id: f for f in field_list}

        # Iterate over all subsets; ensure top_id included
        for r in range(1, m+1):
            for combo in combinations(ids, r):
                if top_id not in combo:
                    continue
                req_sum = sum(required.get(fid, 0) for fid in combo)
                if req_sum > total_drones:
                    continue
                # objective: maximize sum of threat_level of fields in combo
                value = sum(id_to_field[fid].threat_level for fid in combo)
                # Tie-break: prefer smaller req_sum
                if value > best_value or (abs(value - best_value) < 1e-12 and (best_required_sum is None or req_sum < best_required_sum)):
                    best_value = value
                    best_required_sum = req_sum
                    best_subset = set(combo)

        chosen_set = best_subset

        # ASSIGNMENT PHASE
        assigned: Dict[int, str] = {}

        # 1) Preserve drones that currently target fields in chosen_set
        for fid in chosen_set:
            for idx in current_targeting.get(fid, []):
                assigned[idx] = fid

        # 2) For each chosen field, fill up to required using untargeted drones (closest first)
        # Build the list of untargeted (comp.target_id is None and not already assigned)
        untargeted = [i for i in indices if components[i].target_id is None and i not in assigned]

        # For deterministic order
        untargeted.sort()

        for fid in chosen_set:
            need = max(0, required.get(fid, 0) - sum(1 for idx, f2 in assigned.items() if f2 == fid))
            if need <= 0:
                continue
            # choose closest untargeted drones
            untargeted.sort(key=lambda i: distance(i, centers[fid]))
            take = untargeted[:need]
            for i in take:
                assigned[i] = fid
            # remove taken from untargeted
            untargeted = [i for i in untargeted if i not in take]

        # 3) If still fields in chosen_set need drones, pick donors from drones currently assigned to fields not in chosen_set
        # Candidate donors: drones currently assigned to any field not in chosen_set (preserved earlier assignments to chosen_set remain)
        # We'll compute cost_metric for each donor and pick smallest ones for needed slots.
        # Build donor pool: all indices not assigned whose current target_id is some field (i.e., assigned to non-chosen) or even those assigned to None (untargeted already used)
        # For donors we prefer those whose removal causes least loss.
        donor_pool = []
        # Build mapping from field id to its threat for loss calculation
        field_by_id = {f.id: f for f in threatened}
        for i in indices:
            if i in assigned:
                continue  # already assigned to chosen_set
            tid = components[i].target_id
            if tid is None:
                continue  # untargeted already used above; leave here as possible donor if needed
            # compute loss_if_removed for donor's field (approximate)
            if tid in field_by_id:
                denom = max(1, required.get(tid, 0))
                loss_if_removed = field_by_id[tid].threat_level / float(denom) if denom > 0 else 0.0
            else:
                loss_if_removed = 0.0
            # arrival to potential targets will be computed per-target; for ranking donors globally we compute
            # approximate arrival to top (as heuristic) because donors will likely help fields in chosen_set (including top)
            arrival_to_top = distance(i, centers[top_id]) / DRONE_SPEED
            effectiveness = 1.0 / (1.0 + arrival_to_top)
            # cost metric: lower is better
            cost_metric = (loss_if_removed / effectiveness) if effectiveness > 0 else float('inf')
            donor_pool.append((cost_metric, arrival_to_top, i, tid, loss_if_removed))

        # sort donors by cost_metric asc, arrival asc, index
        donor_pool.sort(key=lambda t: (t[0], t[1], t[2]))

        # For each chosen field still needing drones, take donors in a field-by-field manner,
        # preferring donors closer to that field (we'll re-evaluate donor_pool per field)
        # Recompute available donors set
        available_donors = {entry[2] for entry in donor_pool}

        for fid in chosen_set:
            need = max(0, required.get(fid, 0) - sum(1 for idx, f2 in assigned.items() if f2 == fid))
            if need <= 0:
                continue
            if not available_donors:
                break
            # For this fid compute donor list sorted by (cost_metric_to_this_field)
            donor_list = []
            for i in list(available_donors):
                # compute loss_if_removed: if donor currently targets a field in field_by_id
                tid = components[i].target_id
                if tid in field_by_id:
                    denom = max(1, required.get(tid, 0))
                    loss_if_removed = field_by_id[tid].threat_level / float(denom) if denom > 0 else 0.0
                else:
                    loss_if_removed = 0.0
                arrival = distance(i, centers[fid]) / DRONE_SPEED
                effectiveness = 1.0 / (1.0 + arrival)
                cost_metric = (loss_if_removed / effectiveness) if effectiveness > 0 else float('inf')
                donor_list.append((cost_metric, arrival, i, tid, loss_if_removed))
            donor_list.sort(key=lambda t: (t[0], t[1], t[2]))
            take = donor_list[:need]
            for entry in take:
                _, _, i, _, _ = entry
                assigned[i] = fid
                if i in available_donors:
                    available_donors.remove(i)

        # 4) All fields in chosen_set are now assigned as far as possible. If some still not fully filled, we couldn't get enough drones.
        # Next: leftover drones (indices not in assigned) can be used for partial protection of other fields by marginal benefit.
        remaining = [i for i in indices if i not in assigned]

        # Recompute assigned counts
        assigned_count: Dict[str, int] = {}
        for f in threatened:
            fid = f.id
            assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)

        # Marginal per-drone assignment for remaining drones
        # Marginal benefit for assigning drone i to field f:
        #   marginal = (f.threat_level / max(1, required[f])) / (1 + arrival_time)
        # Devalue assignment to fields already fully protected
        for i in sorted(remaining):
            best_val = 0.0
            best_fid = None
            for f in threatened:
                fid = f.id
                req = max(1, required.get(fid, 0))
                base = f.threat_level / float(req)
                if assigned_count.get(fid, 0) >= required.get(fid, 0):
                    # devalue extra drones for fully protected fields
                    base *= 0.2
                arrival = distance(i, centers[fid]) / DRONE_SPEED
                val = base / (1.0 + arrival)
                # deterministic tie-breaker by field id
                if val > best_val or (abs(val - best_val) < 1e-12 and (best_fid is None or str(fid) < str(best_fid))):
                    best_val = val
                    best_fid = fid
            if best_fid is not None and best_val > 0.0:
                assigned[i] = best_fid
                assigned_count[best_fid] = assigned_count.get(best_fid, 0) + 1
            else:
                # leave unassigned -> will go idle
                pass

        # 5) Finalize: assign every component to group
        protecting_groups = {g for g in group_ids if g.startswith(protecting_prefix)}
        for i, comp in enumerate(components):
            if i in assigned:
                fid = assigned[i]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    # fallback: any protecting group or idle or first group
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