from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        DRONE_SPEED = 2.0
        EPS = 1e-8
        PROTECT_STEAL_PENALTY = 1.35  # penalty factor to reassign a drone that is currently protecting another field
        MOVE_STEAL_PENALTY = 1.10     # penalty factor to reassign a drone that is moving to another field

        # distance from point (px,py) to rectangle [left,right] x [top,bottom]
        def dist_to_rect(px, py, field):
            left, right = field.left, field.right
            top, bottom = field.top, field.bottom
            dx = 0.0
            if px < left:
                dx = left - px
            elif px > right:
                dx = px - right
            dy = 0.0
            if py < top:
                dy = top - py
            elif py > bottom:
                dy = py - bottom
            return math.hypot(dx, dy)

        # actual arrival time (no penalty) for drone to reach field
        def arrival_time(drone, field):
            # If already protecting this field -> zero arrival time
            if getattr(drone, "state", None) == "protecting" and drone.target_id == field.id:
                return 0.0
            px = getattr(drone.location, "x", 0)
            py = getattr(drone.location, "y", 0)
            d = dist_to_rect(px, py, field)
            return d / DRONE_SPEED

        # penalized time used to prefer drones that don't require disruptive reassignments
        def penalized_time(drone, field):
            at = arrival_time(drone, field)
            # No penalty if drone is already targeting this field (protecting or moving_to_field)
            if getattr(drone, "target_id", None) == field.id:
                return at
            # If drone is protecting another field, apply protect penalty
            if getattr(drone, "state", None) == "protecting":
                return at * PROTECT_STEAL_PENALTY
            # If drone is moving to another field, apply move penalty
            if getattr(drone, "state", None) == "moving_to_field":
                return at * MOVE_STEAL_PENALTY
            # idle drones -> no extra penalty
            return at

        idle_group = "idle"
        fields = list(getattr(environment, "fields", []) or [])
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # nothing to protect -> idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # deterministic ordering and ensure top field is first
        threatened.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"

        # Precompute penalized and actual times for each drone-field pair
        drone_field_penalized = {}  # (drone, field.id) -> penalized_time
        drone_field_actual = {}     # (drone, field.id) -> actual arrival_time
        for d in components:
            for f in threatened:
                key = (d, f.id)
                at = arrival_time(d, f)
                drone_field_actual[key] = at
                drone_field_penalized[key] = penalized_time(d, f)

        total_drones = len(components)

        # Helper: choose the best k drones for a field based on penalized time
        def best_k_drones_for_field(field, k, exclude_set):
            # exclude_set contains drones already chosen for other fields
            candidates = []
            for d in components:
                if d in exclude_set:
                    continue
                key = (d, field.id)
                candidates.append((drone_field_penalized[key], d))
            candidates.sort(key=lambda x: x[0])
            return [d for _, d in candidates[:k]]

        # Evaluate each field: estimate completion time and value if we allocate the required number of drones
        field_info = {}  # field.id -> dict with required, completion_time, value, candidate_drones
        for f in threatened:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                # cannot protect (or no drones required); treat as zero value
                field_info[f.id] = {"field": f, "required": 0, "completion": float("inf"), "value": 0.0, "candidates": []}
                continue
            # pick best req drones among all drones (we'll allow reassignments in evaluation)
            best = best_k_drones_for_field(f, req, exclude_set=set())
            if len(best) < req:
                # not enough drones to ever fully protect this field now
                field_info[f.id] = {"field": f, "required": req, "completion": float("inf"), "value": 0.0, "candidates": best}
                continue
            # completion time approximated by max penalized time among chosen drones
            penalized_times = [drone_field_penalized[(d, f.id)] for d in best]
            completion = max(penalized_times) if penalized_times else float("inf")
            # value modeled as threat_level divided by completion time (faster completion -> more benefit)
            # small epsilon to avoid divide by zero
            value = float(getattr(f, "threat_level", 0.0)) / (completion + EPS)
            field_info[f.id] = {"field": f, "required": req, "completion": completion, "value": value, "candidates": best}

        # Always select top_field first (mandatory), even if it uses many drones
        selected_fields = []
        assignments = {}  # drone -> field.id assigned
        remaining_drones_set = set(components)

        # Allocate for top field: pick contributors (already targeting) first, then nearest others
        def contributors_for_field(field):
            contrib = []
            for d in components:
                if getattr(d, "target_id", None) == field.id and getattr(d, "state", None) in ("protecting", "moving_to_field"):
                    contrib.append(d)
            return contrib

        # allocate_top
        top_req = int(getattr(top_field, "drones_for_full_protection", 0))
        top_contrib = contributors_for_field(top_field)
        # assign contributors
        for d in top_contrib:
            assignments[d] = top_field.id
            if d in remaining_drones_set:
                remaining_drones_set.remove(d)
        need = max(0, top_req - len(top_contrib))
        if need > 0:
            # pick nearest remaining drones by penalized time
            candidates = sorted([(drone_field_penalized[(d, top_field.id)], d) for d in remaining_drones_set], key=lambda x: x[0])
            to_take = [d for _, d in candidates[:need]]
            for d in to_take:
                assignments[d] = top_field.id
                if d in remaining_drones_set:
                    remaining_drones_set.remove(d)
        selected_fields.append(top_field.id)

        # Now select other fields by greedy value-per-drone (value / required) under available drones
        # Recompute field_info for fields to account for the fact top_field drones are no longer available
        # We'll re-evaluate candidates per field ignoring drones already assigned (assignments)
        available_count = len(remaining_drones_set)
        other_fields = [f for f in threatened if f.id != top_field.id]

        # Prepare a list of candidate field evaluations: compute value/req using best k from remaining pool (but allow using already assigned drones? No - we only consider remaining)
        def evaluate_field_with_current_pool(f, pool_set):
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                return {"required": 0, "completion": float("inf"), "value": 0.0, "candidates": []}
            # include contributing drones already assigned to this field (if any)
            already_assigned = [d for d, fid in assignments.items() if fid == f.id]
            cur = len(already_assigned)
            need = max(0, req - cur)
            # Build pool excluding drones assigned elsewhere
            pool = [d for d in pool_set if d not in already_assigned]
            if len(pool) < need:
                # cannot fulfill
                return {"required": req, "completion": float("inf"), "value": 0.0, "candidates": already_assigned}
            # pick best 'need' drones from pool
            scored = sorted([(drone_field_penalized[(d, f.id)], d) for d in pool], key=lambda x: x[0])
            chosen = already_assigned + [d for _, d in scored[:need]]
            penalized_times = [drone_field_penalized[(d, f.id)] for d in chosen]
            completion = max(penalized_times) if penalized_times else float("inf")
            value = float(getattr(f, "threat_level", 0.0)) / (completion + EPS)
            return {"required": req, "completion": completion, "value": value, "candidates": chosen}

        # Greedy pick by score = value / required
        remaining_pool = set(remaining_drones_set)
        candidate_fields = [f for f in other_fields]
        # Evaluate each
        evals = {}
        for f in candidate_fields:
            evals[f.id] = evaluate_field_with_current_pool(f, remaining_pool)

        # Sort by value/required descending and pick if enough drones available
        # iterate until no more fields can be selected
        while True:
            best_field = None
            best_metric = 0.0
            best_eval = None
            for f in candidate_fields:
                info = evals.get(f.id)
                if not info:
                    continue
                req = info["required"]
                if req <= 0 or info["value"] <= 0.0:
                    continue
                # how many additional drones does this field still need (beyond those already assigned to it)
                already_assigned_here = [d for d, fid in assignments.items() if fid == f.id]
                need = max(0, req - len(already_assigned_here))
                if need == 0:
                    # already satisfied; skip (shouldn't happen)
                    continue
                if len(remaining_pool) < need:
                    continue
                metric = info["value"] / float(req)
                if metric > best_metric:
                    best_metric = metric
                    best_field = f
                    best_eval = info
            if best_field is None:
                break
            # allocate drones for best_field according to best_eval.candidates, but only use drones currently free in remaining_pool
            chosen = []
            for d in best_eval["candidates"]:
                if d in assignments and assignments[d] != best_field.id:
                    # skip drones assigned to other fields
                    continue
                if d in remaining_pool:
                    chosen.append(d)
            # If not enough chosen (rare), attempt to pick additional nearest from remaining_pool
            req = best_eval["required"]
            already_assigned_here = [d for d, fid in assignments.items() if fid == best_field.id]
            need = max(0, req - len(already_assigned_here) - len(chosen))
            if need > 0:
                extra = best_k_drones_for_field(best_field, need, exclude_set=set(assignments.keys()))
                # filter to those in remaining_pool
                extra = [d for d in extra if d in remaining_pool]
                chosen.extend(extra[:need])
            # If still not enough, skip this field
            if len(already_assigned_here) + len(chosen) < req:
                # mark this field as not selectable
                candidate_fields = [ff for ff in candidate_fields if ff.id != best_field.id]
                for ff in candidate_fields:
                    evals[ff.id] = evaluate_field_with_current_pool(ff, remaining_pool)
                continue
            # Assign chosen drones
            for d in chosen:
                assignments[d] = best_field.id
                if d in remaining_pool:
                    remaining_pool.remove(d)
            selected_fields.append(best_field.id)
            # update pool and reevaluate remaining fields
            candidate_fields = [ff for ff in candidate_fields if ff.id != best_field.id]
            for ff in candidate_fields:
                evals[ff.id] = evaluate_field_with_current_pool(ff, remaining_pool)

        # At this point, assignments holds drones assigned to selected fields (including top); others remain unassigned -> idle
        # Finally produce environment.assign_group calls for every drone explicitly
        for d in components:
            assigned_field_id = assignments.get(d)
            if assigned_field_id is None:
                group = idle_group
            else:
                group = f"protecting {assigned_field_id}"
            if group not in group_ids:
                group = idle_group
            environment.assign_group(d, group)