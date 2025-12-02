Reasoning and strategy

Goal: reduce crop damage by making better choices about which fields to fully protect given a limited drone fleet, while still always fully protecting the single most threatened field. Improvements over prior attempts:

- Choose a subset of fields to fully protect (given the drone budget) that maximizes expected threat reduction per drone. This is a knapsack-like selection where each field i requires k_i drones and has value proportional to its threat_level. We use value per drone = threat_level / k_i as the base metric.
- Favor fields that are quick to reach: for each field we compute an estimated arrival time for the k_i nearest drones and reduce the field's score by an exponential decay of that arrival time. This prioritizes fields we can secure quickly (so protection starts sooner).
- Always include the top-threat field, regardless of cost — it must be fully protected.
- Preserve existing protecting drones for the fields we plan to protect (to avoid churn) and prefer to assign nearby idle/moving drones next. If still short, reassign drones from fields we decided not to protect, starting with the lowest-value fields.
- If after fully protecting the selected subset we still have leftover drones that cannot fully secure another field, use them to partially protect the next-best field (partial protection still helps somewhat).
- Deterministic tie-breaking ensures stable behavior.

This approach aims to maximize the expected protected threat given travel times and available drones, starting protection sooner and reducing reassignments.

```py
from typing import List, Dict, Tuple
import math
from math import exp
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Allocation strategy:
        - Always fully protect the highest-threat field.
        - Greedily select additional fields to fully protect by maximizing an adjusted
          score = (threat / drones_required) * exp(-gamma * avg_arrival_time_for_k_nearest_drones).
        - Preserve existing protectors for chosen fields, then assign nearest unassigned drones,
          then (if necessary) reassign from deselected fields with lowest value.
        - If leftover drones are insufficient to fully protect another field, assign them to partially
          protect the best remaining field.
        - Assign every drone either to a protecting group ("protecting {field.id}") or "idle".
        """
        # Parameters
        SPEED = 2.0            # drone speed
        GAMMA = 0.9            # decay for arrival time (higher => prefer quick-to-reach fields more strongly)
        RETENTION_BONUS = 1.2  # boost for drones already protecting a chosen field (reduces churn)

        def center(field):
            return ((getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0,
                    (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0)

        def dist(loc, c):
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - c[0]
            dy = getattr(loc, "y", 0) - c[1]
            return math.hypot(dx, dy)

        # Threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Deterministic sort by threat desc, id tie-break
        fields.sort(key=lambda f: (getattr(f, "threat_level", 0), str(getattr(f, "id", ""))), reverse=True)
        top_field = fields[0]

        # Precompute centers and requirements and base values
        centers = {f.id: center(f) for f in fields}
        reqs = {f.id: int(getattr(f, "drones_for_full_protection", 0)) for f in fields}
        threats = {f.id: getattr(f, "threat_level", 0) for f in fields}

        # Drone info
        total_drones = len(components)
        drone_locs = {c: getattr(c, "location", None) for c in components}

        # Current protecting drones per threatened field
        protecting_current: Dict[str, List] = {f.id: [] for f in fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tgt = getattr(c, "target_id", None)
                if tgt in protecting_current:
                    protecting_current[tgt].append(c)

        # Precompute distances and arrival times: for each field, sorted list of (drone, time)
        distances: Dict[str, List[Tuple[object, float]]] = {}
        for f in fields:
            c = centers[f.id]
            lst = []
            for comp in components:
                d = dist(drone_locs.get(comp), c)
                t = d / SPEED
                lst.append((comp, t))
            lst.sort(key=lambda x: (x[1], str(getattr(x[0], "target_id", "")), str(getattr(x[0], "state", ""))))
            distances[f.id] = lst

        # Compute adjusted score for each field:
        # score = (threat / req) * exp(-GAMMA * avg_time_of_k_nearest)
        field_scores: List[Tuple[float, str]] = []
        for f in fields:
            fid = f.id
            k = max(1, reqs.get(fid, 0))
            base = threats.get(fid, 0) / k
            # average arrival time of k nearest drones
            times = [t for (_, t) in distances[fid][:k]]
            avg_time = sum(times) / len(times) if times else float("inf")
            adjusted = base * math.exp(-GAMMA * avg_time)
            field_scores.append((adjusted, fid))

        # Ensure top_field is included. Greedily choose other fields by adjusted score until drones used up.
        # Budget is total_drones
        budget = total_drones
        chosen_fields: List[str] = []

        # Always include top field
        top_k = reqs.get(top_field.id, 0)
        if top_k < 0:
            top_k = 0
        # If top requires more drones than exist, we'll still attempt to assign as many as possible.
        chosen_fields.append(top_field.id)
        budget -= top_k
        # Sort other fields by score desc (tie-break by id)
        remaining_scores = sorted([fs for fs in field_scores if fs[1] != top_field.id],
                                  key=lambda x: (-x[0], str(x[1])))

        for score, fid in remaining_scores:
            k = reqs.get(fid, 0)
            if k <= 0:
                continue
            if k <= budget:
                chosen_fields.append(fid)
                budget -= k
            # otherwise skip (we will consider partial assignment later)
        # budget may be negative if top_k > total_drones; that's handled later

        # Assignment map: comp -> field_id for protection
        assign_map: Dict[object, str] = {}

        # STEP: For each chosen field, keep existing protectors there (if any), then fill up with nearest available drones.
        # Keep set of used drones
        used: set = set()

        # Helper to pick nearest N from a list excluding used set
        def pick_nearest(fid, needed):
            out = []
            for comp, t in distances[fid]:
                if comp in used:
                    continue
                out.append(comp)
                if len(out) >= needed:
                    break
            return out

        # First fill top field
        top_need = max(0, reqs.get(top_field.id, 0) - len(protecting_current.get(top_field.id, [])))
        # Keep existing top protectors
        for c in protecting_current.get(top_field.id, []):
            assign_map[c] = top_field.id
            used.add(c)
        # Choose nearest other drones to fill top_need
        if top_need > 0:
            nearest = pick_nearest(top_field.id, top_need)
            for c in nearest:
                assign_map[c] = top_field.id
                used.add(c)

        # For other chosen fields
        for fid in chosen_fields:
            if fid == top_field.id:
                continue
            # Keep existing protectors
            kept = protecting_current.get(fid, []).copy()
            for c in kept:
                if c in used:
                    # if already used elsewhere skip (rare if it was assigned to top); we won't double-assign
                    continue
                assign_map[c] = fid
                used.add(c)
            need = max(0, reqs.get(fid, 0) - sum(1 for c in protecting_current.get(fid, []) if c in assign_map and assign_map.get(c) == fid))
            if need > 0:
                nearest = pick_nearest(fid, need)
                for c in nearest:
                    assign_map[c] = fid
                    used.add(c)

        # If after the above some chosen fields are still under-protected (e.g., because top consumed many drones),
        # we should try to reassign drones from non-chosen fields (prefer those with lowest value per drone).
        # Build list of drones currently protecting non-chosen fields
        non_chosen_fields = [f for f in fields if f.id not in chosen_fields]
        # Sort non-chosen fields by their base value per drone (asc) to take from least valuable fields first
        non_chosen_sorted = sorted(non_chosen_fields, key=lambda f: ( (threats.get(f.id,0) / max(1, reqs.get(f.id,0)) ), str(f.id) ))
        # For each chosen field that is still short, try to reassign protectors from non_chosen_sorted
        for fid in chosen_fields:
            required = reqs.get(fid, 0)
            have = sum(1 for c, t in assign_map.items() if t == fid)
            if have >= required:
                continue
            need = required - have
            # gather donor drones from low-value non-chosen fields
            donors = []
            for nf in non_chosen_sorted:
                for c in protecting_current.get(nf.id, []):
                    if c in used:
                        continue
                    donors.append((nf.id, c))
                if len(donors) >= need:
                    break
            # If still not enough donors, also consider any drones assigned to other non-top chosen fields (but prefer not to)
            if len(donors) < need:
                # take from other chosen fields with surplus (those with more assigned than required)
                for other in chosen_fields:
                    if other == fid:
                        continue
                    other_have = sum(1 for c in assign_map if assign_map.get(c) == other)
                    other_req = reqs.get(other, 0)
                    if other_have > other_req:
                        # collect surplus
                        for c in [c for c in assign_map if assign_map.get(c) == other]:
                            if c in used:
                                continue
                            donors.append((other, c))
                            if len(donors) >= need:
                                break
                # if still insufficient, consider any non-used drones (idle/moving)
                if len(donors) < need:
                    for c in components:
                        if c in used:
                            continue
                        donors.append((None, c))
                        if len(donors) >= need:
                            break
            # reassign donors to fid
            for i in range(min(need, len(donors))):
                _, comp = donors[i]
                assign_map[comp] = fid
                used.add(comp)

        # After trying to secure chosen fields, compute how many drones are assigned
        protected_count = len(assign_map)

        # If budget remaining (i.e., we have unassigned drones) but they are insufficient to fully cover any remaining field,
        # we assign them to partially protect the next best field (by adjusted score) to still help reduce damage.
        unassigned = [c for c in components if c not in assign_map]
        # Determine next-best non-chosen field by adjusted score (recompute only for non-chosen)
        non_chosen = [fs for fs in field_scores if fs[1] not in chosen_fields]
        if non_chosen:
            non_chosen.sort(key=lambda x: (-x[0], str(x[1])))
            # pick the best remaining field
            best_remain_score, best_fid = non_chosen[0]
            # Try to assign all unassigned drones to partially protect this field (limited benefit but better than idle)
            # But avoid stealing from top_field. Only use unassigned drones here.
            for c in unassigned:
                assign_map[c] = best_fid
            used.update(unassigned)

        # Final safety: ensure top_field has at least as many drones as possible (if top required > available we assigned what we can)
        # Now perform environment.assign_group for every component
        valid_groups = set(group_ids)
        for comp in components:
            if comp in assign_map:
                gid = f"protecting {assign_map[comp]}"
                if gid in valid_groups:
                    environment.assign_group(comp, gid)
                else:
                    environment.assign_group(comp, "idle")
            else:
                # If comp was already protecting a threatened field and that field still exists, keep it to reduce churn
                prev_state = getattr(comp, "state", None)
                prev_tgt = getattr(comp, "target_id", None)
                if prev_state == "protecting" and prev_tgt in centers:
                    gid = f"protecting {prev_tgt}"
                    if gid in valid_groups:
                        environment.assign_group(comp, gid)
                        continue
                environment.assign_group(comp, "idle")
```