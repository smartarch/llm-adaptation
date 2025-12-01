Reasoning and adaptation strategy

What I'll change and why
- The previous strategy that gave good reductions preserved existing assignments and preferred untargeted drones when building up the top field. We can improve further by making the selection of donor drones for the top field more cost-aware: when we must reassign drones from other fields to satisfy the hard rule (fully protect the highest-threat field), pick donors that minimize the expected damage increase elsewhere relative to how quickly they will become effective at the top field.
- Concretely, for each candidate donor drone we compute:
  - loss_if_removed = approximate damage contribution lost at its current field if we remove it (threat_of_field / max(1, drones_for_full_protection)).
  - effectiveness = 1 / (1 + arrival_time_to_top) (captures delay in becoming effective at top).
  - cost_metric = loss_if_removed / effectiveness (we prefer donors with smallest cost_metric).
  This favors untargeted drones (loss=0), drones assigned to low-value fields, and drones that arrive quickly to the top.
- For assigning remaining drones to other fields, improve full-protection scoring by using average arrival time of the drone set needed for full protection (sum(arrival_times)/needed) so we prefer fields that can be fully protected quickly on average. If we cannot fully protect a field, we assign leftover drones greedily by per-drone marginal benefit that includes arrival time and remaining fraction to full protection.
- Keep all earlier good habits: preserve current targeters initially, always fully protect the highest-threat field, deterministic tie-breaks.

This should reduce unnecessary harm caused by pulling valuable drones away from other fields and prioritize donors that give the fastest and least harmful reinforcement to the top field.

Implementation (class SmartFarmAdaptation):

```py
from math import hypot
from typing import Dict, List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved donor selection and assembly-time-aware allocation.

        - Preserve current targetings initially.
        - Ensure top-threat field is fully protected:
          * Prefer untargeted drones, then reassign donors chosen by minimal cost_metric:
            cost_metric = loss_if_removed / (1 / (1 + arrival_time_to_top))
            where loss_if_removed approximates lost protection at donor's field.
        - Greedily fully protect other fields using closest available drones, using average arrival time in scoring.
        - Assign remaining drones one-by-one by marginal benefit (threat/required adjusted by arrival time).
        - Unassigned -> idle.
        """
        DRONE_SPEED = 2.0

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_point_to_drone(point, comp_idx):
            c = components[comp_idx]
            dx = c.location.x - point[0]
            dy = c.location.y - point[1]
            return hypot(dx, dy)

        idle_group = "idle"
        protecting_prefix = "protecting "

        # Indexable components
        n = len(components)
        indices = list(range(n))

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else "idle")
            for comp in components:
                environment.assign_group(comp, target)
            return

        # Choose top field (highest threat, tie break by id)
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

        # Map current targeting (from observed comp.target_id)
        current_targeting: Dict[str, List[int]] = {}
        for i, comp in enumerate(components):
            tid = comp.target_id
            if tid is not None:
                current_targeting.setdefault(tid, []).append(i)

        # Assigned mapping: index -> field_id (we'll fill and then apply)
        assigned: Dict[int, str] = {}

        # Preserve all current targetings
        for fid, lst in current_targeting.items():
            for idx in lst:
                assigned[idx] = fid

        # Ensure top field fully protected: count how many already assigned to top
        top_assigned = [i for i, fid in assigned.items() if fid == top_id]
        top_assigned_count = len(top_assigned)
        top_required = required.get(top_id, 0)
        if top_assigned_count < top_required:
            need = top_required - top_assigned_count
            # 1) Prefer untargeted drones (comp.target_id is None and not already assigned)
            untargeted = [i for i in indices if components[i].target_id is None and i not in assigned]
            untargeted.sort(key=lambda i: distance_point_to_drone(centers[top_id], i))
            take = untargeted[:need]
            for i in take:
                assigned[i] = top_id
            need -= len(take)

            # 2) If still need, select donor drones from other fields using cost metric
            if need > 0:
                # Build donor candidates: any drone not assigned to top (including those preserved on other fields)
                donor_candidates = []
                # Helper map from field id to its threat for lookup
                field_by_id = {f.id: f for f in threatened}
                for i in indices:
                    if i in assigned and assigned.get(i) == top_id:
                        continue  # skip those already on top
                    if i in assigned:
                        donor_field = assigned[i]
                    else:
                        donor_field = components[i].target_id  # could be None
                    # Compute loss_if_removed
                    if donor_field is None or donor_field not in field_by_id:
                        loss_if_removed = 0.0
                    else:
                        fobj = field_by_id[donor_field]
                        denom = max(1, required.get(donor_field, 0))
                        loss_if_removed = fobj.threat_level / float(denom) if denom > 0 else 0.0
                    arrival = distance_point_to_drone(centers[top_id], i) / DRONE_SPEED
                    effectiveness = 1.0 / (1.0 + arrival)
                    # Avoid division by zero; if effectiveness extremely small, set large cost
                    if effectiveness <= 0:
                        cost_metric = float('inf')
                    else:
                        cost_metric = loss_if_removed / effectiveness
                    # For deterministic tie-breaking, include arrival and index
                    donor_candidates.append((cost_metric, arrival, i, donor_field, loss_if_removed))
                # Sort donors by cost_metric ascending, then by arrival ascending, then index
                donor_candidates.sort(key=lambda t: (t[0], t[1], t[2]))
                # Choose as many as needed that are available (excluding those already assigned to top)
                chosen = []
                for entry in donor_candidates:
                    if need <= 0:
                        break
                    _, _, i, donor_field, _ = entry
                    # skip if this drone is already assigned to top (shouldn't be)
                    if assigned.get(i) == top_id:
                        continue
                    # Assign it (we overwrite its previous assignment)
                    assigned[i] = top_id
                    chosen.append(i)
                    need -= 1
                # If still need (no donors available), we'll do best-effort (can't fulfill fully)
                # proceed with whatever assigned.

        # After top satisfied as much as possible, proceed to protect other fields.
        # Compute current assigned_count per field
        assigned_count: Dict[str, int] = {}
        for f in threatened:
            fid = f.id
            assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)

        # Available drones are those not assigned yet
        available = [i for i in indices if i not in assigned]

        # Attempt to fully protect other fields greedily by benefit using average arrival time
        other_fields = [f for f in threatened if f.id != top_id]
        # For each field compute need and a score if enough available
        field_scores = []
        for f in other_fields:
            fid = f.id
            need = max(0, required.get(fid, 0) - assigned_count.get(fid, 0))
            if need <= 0:
                continue
            # Find closest 'need' available drones; if not enough available, skip full-protection attempt
            if len(available) < need:
                continue
            dists = sorted((distance_point_to_drone(centers[fid], i), i) for i in available)
            chosen = [i for (_, i) in dists[:need]]
            # average arrival time
            avg_arrival = sum(d for (d, _) in dists[:need]) / float(need) / DRONE_SPEED
            # score balances threat and average arrival and drones needed
            score = f.threat_level / ((1.0 + avg_arrival) * max(1, need))
            field_scores.append((score, f, chosen, avg_arrival))
        # Sort fields by score descending
        field_scores.sort(key=lambda t: (-t[0], str(t[1].id)))

        # Assign chosen drones for each field in order
        for score, f, chosen, avg_arrival in field_scores:
            fid = f.id
            # recompute current need
            need = max(0, required.get(fid, 0) - assigned_count.get(fid, 0))
            if need <= 0:
                continue
            # filter chosen to those still available
            chosen_filtered = [i for i in chosen if i in available]
            take = min(len(chosen_filtered), need)
            for i in chosen_filtered[:take]:
                assigned[i] = fid
                assigned_count[fid] = assigned_count.get(fid, 0) + 1
            # update available
            available = [i for i in available if i not in assigned]

        # Assign remaining drones one-by-one by marginal benefit (time-aware)
        available = [i for i in indices if i not in assigned]
        if available:
            # recompute assigned_count
            assigned_count = {}
            for f in threatened:
                fid = f.id
                assigned_count[fid] = sum(1 for idx, fid2 in assigned.items() if fid2 == fid)
            # For each available drone choose best field
            while available:
                best_val = 0.0
                best_pair = None  # (drone_idx, field_id)
                for i in available:
                    for f in threatened:
                        fid = f.id
                        req = max(1, required.get(fid, 0))
                        if assigned_count.get(fid, 0) >= required.get(fid, 0):
                            # field already fully protected; devalue additional drones
                            base = (f.threat_level / float(req)) * 0.2
                        else:
                            base = (f.threat_level / float(req))
                        arrival = distance_point_to_drone(centers[fid], i) / DRONE_SPEED
                        val = base / (1.0 + arrival)
                        # deterministic tie-break by drone idx and field id
                        if val > best_val or (abs(val - best_val) < 1e-12 and best_pair is not None and (i < best_pair[0] or (i == best_pair[0] and str(fid) < str(best_pair[1])))):
                            best_val = val
                            best_pair = (i, fid)
                if best_pair is None or best_val <= 0.0:
                    break
                di, fid = best_pair
                assigned[di] = fid
                assigned_count[fid] = assigned_count.get(fid, 0) + 1
                available = [i for i in available if i != di]

        # Any remaining unassigned drones will be idle
        # Finalize assignments via environment.assign_group for every component
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
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0] if group_ids else "idle")
```