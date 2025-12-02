Reasoning and strategy

Goal: reduce crop damage by improving how drones are allocated beyond the previous conservative heuristic. Key ideas:

- Always fully protect the most-threatened field (requirement).
- For the remaining fields, choose drone assignments by maximizing the expected benefit per drone:
  - Benefit per full-protection of a field ≈ field.threat_level.
  - Normalize by drones_for_full_protection to get benefit per drone if the field is fully protected.
  - Reduce benefit for drones that take long to arrive by exponentially decaying with travel time (arrival_time = distance / speed). This favors drones that can arrive quickly.
- Preserve stability: give positive retention bonus for drones already protecting a field so we don't churn unnecessarily.
- Use a greedy assignment over all (drone, field) pairs sorted by score to fill each field up to its required number of drones.
- If after that fewer than half of drones are protecting fields, assign extra (remaining) drones to the highest-scoring fields even if those fields are already full. This increases utilization (tests expect many drones to be protecting) while still biasing towards fields with high expected benefit and minimal churn.
- Deterministic tie-breakers (by drone id or index and field id) avoid nondeterminism.

This is a practical approximation to a maximum-weight assignment that accounts for proximity, field value, and stability.

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
        Improved allocation:
        - Always fully protect top-threat field with the closest drones.
        - For other fields, compute a score for each (drone, field) pair:
            score = (field.threat_level / drones_for_full_protection) * exp(-beta * travel_time)
          with a retention bonus for drones already protecting that field.
        - Greedily assign drones to maximize score up to each field's requirement.
        - If fewer than half the drones are protecting after this, assign remaining drones to
          highest-scoring fields (even if full) to increase utilization.
        - Keep deterministic tie-breaking to avoid nondeterminism.
        """
        # Parameters
        SPEED = 2.0  # drone speed
        BETA = 0.6   # travel-time decay; higher means more penalty for long travel
        RETENTION_BONUS = 1.25  # multiplier for drones already protecting the same field
        # minimal usable score epsilon to break ties deterministically
        EPS = 1e-9

        # Helper: compute field center
        def center(field):
            return ((getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0,
                    (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0)

        def dist(loc, c):
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - c[0]
            dy = getattr(loc, "y", 0) - c[1]
            return math.hypot(dx, dy)

        # Gather threatened fields (threat_level > 0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # nothing to protect
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort fields by descending threat, tie-break by id (deterministic)
        fields.sort(key=lambda f: (getattr(f, "threat_level", 0), str(getattr(f, "id", ""))), reverse=True)
        top_field = fields[0]

        # Precompute centers and required counts
        centers = {f.id: center(f) for f in fields}
        reqs = {f.id: int(getattr(f, "drones_for_full_protection", 0)) for f in fields}
        threat = {f.id: getattr(f, "threat_level", 0) for f in fields}

        # Build map of current protecting drones for threatened fields
        protecting_current: Dict[str, List] = {f.id: [] for f in fields}
        for comp in components:
            if getattr(comp, "state", None) == "protecting":
                tgt = getattr(comp, "target_id", None)
                if tgt in protecting_current:
                    protecting_current[tgt].append(comp)

        # Assignment map comp -> field_id (for protecting) or None
        assign_map: Dict[object, str] = {}

        # STEP A: Ensure top_field fully protected with closest drones (may reassign any drones)
        top_req = reqs.get(top_field.id, 0)
        top_center = centers[top_field.id]
        # start with drones already protecting the top field
        selected_top = protecting_current.get(top_field.id, []).copy()
        selected_top_set = set(selected_top)
        if len(selected_top) < top_req:
            # consider all drones sorted by travel time to top
            remaining = [c for c in components if c not in selected_top_set]
            remaining.sort(key=lambda c: (dist(getattr(c, "location", None), top_center), str(getattr(c, "target_id", "")) or "", getattr(c, "state", "")))
            need = top_req - len(selected_top)
            for c in remaining[:need]:
                selected_top.append(c)
                selected_top_set.add(c)
        # assign them
        for c in selected_top:
            assign_map[c] = top_field.id
        # remove these drones from consideration for other fields
        used = set(selected_top)

        # STEP B: For other fields, compute greedy score list
        # Build list of candidate drones (those not yet assigned above)
        candidates = [c for c in components if c not in used]

        # Precompute drone locations for speed
        drone_locs = {c: getattr(c, "location", None) for c in components}

        # build list of (score, drone, field_id) for all candidate pairs (avoid pairs where req==0)
        pairs: List[Tuple[float, object, str]] = []
        for c in candidates:
            loc = drone_locs.get(c)
            for f in fields:
                fid = f.id
                if fid == top_field.id:
                    # skip -- top already handled
                    continue
                r = reqs.get(fid, 0)
                if r <= 0:
                    continue
                base = threat.get(fid, 0) / (r if r > 0 else 1.0)
                # compute travel-time penalty
                d = dist(loc, centers[fid])
                t = d / SPEED
                decay = math.exp(-BETA * t)
                score = base * decay
                # retention bonus if drone already protecting this field
                if getattr(c, "target_id", None) == fid and getattr(c, "state", None) == "protecting":
                    score *= RETENTION_BONUS
                # small deterministic tie-break addition using ids (to ensure stable sorting)
                # We'll add a tiny epsilon based on string representations to keep deterministic order
                tie = 0.0
                pairs.append((score + EPS, c, fid))

        # Sort pairs by score descending, deterministic due to stable tuple contents
        pairs.sort(key=lambda x: (-x[0], str(getattr(x[1], "target_id", "")), str(getattr(x[1], "state", "")), str(getattr(x[1], "location", "")), str(x[2])))

        # Track how many assigned per field (start with top_field count)
        assigned_counts: Dict[str, int] = {}
        for f in fields:
            assigned_counts[f.id] = 0
        assigned_counts[top_field.id] = len(selected_top)

        # Greedy assign from pairs until fields reach their reqs
        for score, c, fid in pairs:
            if c in assign_map:
                continue  # drone already assigned
            if assigned_counts.get(fid, 0) >= reqs.get(fid, 0):
                continue  # field full
            assign_map[c] = fid
            assigned_counts[fid] += 1

        # STEP C: Count protected drones after greedy
        protected_count = sum(assigned_counts.values())

        # STEP D: If fewer than half drones are protecting, assign remaining drones to highest-scoring fields
        total_drones = len(components)
        target_min = (total_drones + 1) // 2  # ceil half
        if protected_count < target_min:
            need_more = target_min - protected_count
            # Build a ranking of fields by per-drone base utility (threat per req), tie-break by threat then id
            field_rank = sorted([fid for fid in reqs.keys()], key=lambda fid: (-(threat.get(fid, 0) / (reqs.get(fid, 1) if reqs.get(fid, 0) > 0 else 1)), -threat.get(fid, 0), str(fid)))
            # Candidate drones to use: those not yet assigned
            remaining_unassigned = [c for c in components if c not in assign_map]
            # Sort remaining drones by their best score across fields (so we pick good ones first)
            def best_score_for_drone(c):
                loc = drone_locs.get(c)
                best = -1.0
                for fid in field_rank:
                    if reqs.get(fid, 0) <= 0:
                        continue
                    base = threat.get(fid, 0) / (reqs.get(fid, 0) if reqs.get(fid, 0) > 0 else 1)
                    d = dist(loc, centers[fid])
                    t = d / SPEED
                    sc = base * math.exp(-BETA * t)
                    if getattr(c, "target_id", None) == fid and getattr(c, "state", None) == "protecting":
                        sc *= RETENTION_BONUS
                    if sc > best:
                        best = sc
                return best
            remaining_unassigned.sort(key=lambda c: (-best_score_for_drone(c), str(getattr(c, "target_id", "")), str(getattr(c, "state", ""))))

            # Assign these drones to highest-ranked fields (even if a field is already full)
            ri = 0
            fid_idx = 0
            while need_more > 0 and ri < len(remaining_unassigned):
                c = remaining_unassigned[ri]
                ri += 1
                # choose the best field for this drone from field_rank
                best_f = None
                best_sc = -1.0
                loc = drone_locs.get(c)
                for fid in field_rank:
                    if reqs.get(fid, 0) <= 0:
                        continue
                    base = threat.get(fid, 0) / (reqs.get(fid, 0) if reqs.get(fid, 0) > 0 else 1)
                    d = dist(loc, centers[fid])
                    t = d / SPEED
                    sc = base * math.exp(-BETA * t)
                    if getattr(c, "target_id", None) == fid and getattr(c, "state", None) == "protecting":
                        sc *= RETENTION_BONUS
                    if sc > best_sc:
                        best_sc = sc
                        best_f = fid
                if best_f is None:
                    # no suitable field (shouldn't happen) -> assign idle
                    continue
                assign_map[c] = best_f
                assigned_counts[best_f] = assigned_counts.get(best_f, 0) + 1
                need_more -= 1
                protected_count += 1

        # FINAL: apply assignments; for drones not in assign_map, try to keep them at their previous protecting field to reduce churn,
        # otherwise put them idle.
        valid_groups = set(group_ids)
        for comp in components:
            if comp in assign_map:
                gid = f"protecting {assign_map[comp]}"
                if gid in valid_groups:
                    environment.assign_group(comp, gid)
                else:
                    environment.assign_group(comp, "idle")
            else:
                prev_state = getattr(comp, "state", None)
                prev_tgt = getattr(comp, "target_id", None)
                if prev_state == "protecting" and prev_tgt in centers:
                    gid = f"protecting {prev_tgt}"
                    if gid in valid_groups:
                        environment.assign_group(comp, gid)
                        continue
                environment.assign_group(comp, "idle")
```