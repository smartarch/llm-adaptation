from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Always fully protect the single highest-threat field using closest drones.
        - Penalize reassigning drones that are currently protecting other fields when picking extra drones for the top field.
        - After the top field is secured, greedily assign remaining drones one-by-one to the field
          with the highest marginal benefit = (threat / current_need) / (1 + travel_time),
          where travel_time = distance_to_field / speed (speed == 2).
        - Lock drones protecting fields that were initially fully protected; they are never reassigned.
        """
        # Helper: squared distance to rectangle (0 if inside)
        def dist2_to_rect(x, y, field):
            dx = 0.0
            if x < field.left:
                dx = field.left - x
            elif x > field.right:
                dx = x - field.right
            dy = 0.0
            if y < field.top:
                dy = field.top - y
            elif y > field.bottom:
                dy = y - field.bottom
            return dx * dx + dy * dy

        # Drone speed (given): we'll use it when estimating travel time
        DRONE_SPEED = 2.0

        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Collect threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Choose the single highest-threat field (tie-break by id)
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, f.id))
        target_id = target_field.id
        target_group = f"protecting {target_id}"
        if target_group not in group_ids:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Count current protectors (state == "protecting") per threatened field
        protecting_counts = {f.id: 0 for f in threatened_fields}
        protecting_drones = {f.id: [] for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in protecting_counts:
                    protecting_counts[tid] += 1
                    protecting_drones[tid].append(d)

        # Identify fields initially fully protected and lock those protecting drones
        fully_protected_initial = set()
        for f in threatened_fields:
            cnt = protecting_counts.get(f.id, 0)
            if cnt >= int(f.drones_for_full_protection):
                fully_protected_initial.add(f.id)

        locked_ids = set()
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                locked_ids.add(id(d))

        # Determine drones already committed to the target: protecting OR moving_to_field with target == target_id
        committed_to_target = []
        for d in components:
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if tid == target_id and (st == "protecting" or st == "moving_to_field"):
                committed_to_target.append(d)
        committed_ids = {id(d) for d in committed_to_target}
        already_committed_count = len(committed_to_target)

        required_total = int(target_field.drones_for_full_protection)

        # Final assignments mapping: drone_id -> field_id
        final_assigned = {}

        # Keep locked drones assigned to their fields
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                final_assigned[id(d)] = fid

        # Assign committed drones to the target
        for d in committed_to_target:
            final_assigned[id(d)] = target_id

        # If target not fully committed, select extra drones for it.
        # Penalize reassigning protectors of other fields heavily to avoid increasing damage there unnecessarily.
        if already_committed_count < required_total:
            need = required_total - already_committed_count
            # Candidates: drones not locked and not already committed
            candidates = [d for d in components if id(d) not in locked_ids and id(d) not in committed_ids]

            # Candidate key: primary = distance to target rect (arrive sooner), then prefer moving_to_target,
            # then penalize if currently protecting a different field (large penalty), then id
            def cand_key_for_target(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), target_field)
                st = getattr(d, "state", None)
                tid = getattr(d, "target_id", None)
                moving_pref = 0 if (st == "moving_to_field" and tid == target_id) else 1
                # Penalize reassigning protectors of other fields
                protecting_other_penalty = 0 if (st == "protecting" and tid != target_id and tid in protecting_counts) else 0
                # We'll implement penalty by adding a large constant to distance if protecting other
                PENALTY_DIST_INCR = 1e6 if (st == "protecting" and tid != target_id and tid in protecting_counts) else 0.0
                return (dist2 + PENALTY_DIST_INCR, moving_pref, id(d))

            candidates.sort(key=cand_key_for_target)
            to_take = candidates[:need]
            for d in to_take:
                final_assigned[id(d)] = target_id

        # Build list of available drones for subsequent allocation:
        available_drones = [d for d in components if id(d) not in locked_ids and id(d) not in final_assigned]

        # If no available drones remain, finalize assignments
        if not available_drones:
            for d in components:
                did = id(d)
                if did in final_assigned:
                    gid = final_assigned[did]
                    grp = f"protecting {gid}"
                    environment.assign_group(d, grp if grp in group_ids else idle_group)
                else:
                    environment.assign_group(d, idle_group)
            return

        # Prepare tracking of current assignments per field (include already assigned from final_assigned and protecting_counts)
        assigned_counts = {f.id: 0 for f in threatened_fields}
        # Start with protecting_counts (state == protecting) to reflect existing in-place protectors,
        # but only those not locked that we didn't reassign might be moved; to be conservative, account existing protecting as assigned.
        for fid in assigned_counts:
            assigned_counts[fid] = protecting_counts.get(fid, 0)
        # Apply final_assigned (these include committed to target and newly selected for target)
        for did, fid in final_assigned.items():
            # If a drone was protecting another field originally and now final_assigned says different,
            # we will effectively move it; adjust counts accordingly.
            # We'll recompute counts by reconstructing from final_assigned and protecting_drones:
            pass

        # Recompute assigned_counts based on current protecting drones that we didn't reassign,
        # and on final_assigned which overrides some drones.
        # Start fresh: zero, then count locked protectors (they remain), then count final_assigned, then add other unassigned protectors not moved.
        assigned_counts = {f.id: 0 for f in threatened_fields}
        # locked protectors (these we know are protecting_counts for fully_protected_initial)
        for fid in fully_protected_initial:
            assigned_counts[fid] = protecting_counts.get(fid, 0)
        # Add final_assigned drones
        for did, fid in final_assigned.items():
            if fid in assigned_counts:
                assigned_counts[fid] += 1
        # For protecting drones that are not locked and not moved (i.e., their id not in final_assigned and they are state protecting),
        # count them toward their field
        for f in threatened_fields:
            for d in protecting_drones.get(f.id, []):
                did = id(d)
                if did in locked_ids:
                    # already included
                    continue
                if did in final_assigned:
                    # moved or assigned
                    continue
                # They continue protecting their field
                assigned_counts[f.id] += 1

        # Now do per-drone greedy allocation: repeatedly take the best (drone,field) marginal pair
        # until no available drones.
        # Precompute distances from each drone to each field for speed
        drone_to_field_dist = {}
        for d in available_drones:
            loc = getattr(d, "location", None)
            dx = getattr(loc, "x", 0) if loc is not None else None
            dy = getattr(loc, "y", 0) if loc is not None else None
            drone_to_field_dist[id(d)] = {}
            for f in threatened_fields:
                # skip target_field (it is already handled)
                if f.id == target_id:
                    # still allow assignment to other fields if target needed more? target was already satisfied by now.
                    pass
                if loc is None:
                    drone_to_field_dist[id(d)][f.id] = float("inf")
                else:
                    drone_to_field_dist[id(d)][f.id] = math.sqrt(dist2_to_rect(dx, dy, f))

        # Fields that we consider for allocation: threatened fields (including target only if still needed)
        fields_for_alloc = {f.id: f for f in threatened_fields}

        # Greedy loop
        while available_drones:
            best_pair = None
            best_value = -1.0
            # Evaluate marginal for each (drone, field) pair
            for d in available_drones:
                did = id(d)
                for f in threatened_fields:
                    fid = f.id
                    # Skip assigning to the top field if it already has enough assigned
                    if fid == target_id and assigned_counts.get(fid, 0) >= int(f.drones_for_full_protection):
                        continue
                    # Determine current_need for this field
                    needed = int(f.drones_for_full_protection) - assigned_counts.get(fid, 0)
                    if needed <= 0:
                        # field already fully protected, marginal benefit is low (we could still assign but no extra benefit)
                        current_need = 1
                    else:
                        current_need = needed
                    # travel time estimate
                    dist = drone_to_field_dist.get(did, {}).get(fid, float("inf"))
                    travel_time = dist / DRONE_SPEED
                    # marginal benefit proxy
                    marginal = (f.threat_level / float(max(1, current_need))) / (1.0 + travel_time)
                    # Slightly prefer fields that are not 0 threat (all are), tie-break by shorter travel
                    # Use small epsilon to prefer closer drone if marginal equal
                    if marginal > best_value or (abs(marginal - best_value) < 1e-12 and dist < drone_to_field_dist.get(best_pair[0].__hash__(), {}).get(best_pair[1], float("inf")) if best_pair else False):
                        best_value = marginal
                        best_pair = (d, fid, dist)
            if best_pair is None:
                break
            # Assign the best drone to the best field
            chosen_drone, chosen_fid, chosen_dist = best_pair
            final_assigned[id(chosen_drone)] = chosen_fid
            # Update assigned counts
            assigned_counts[chosen_fid] = assigned_counts.get(chosen_fid, 0) + 1
            # Remove chosen drone from available_drones
            available_drones = [d for d in available_drones if id(d) != id(chosen_drone)]

        # Final assignments: locked protectors (already in final_assigned), final_assigned drones to their fields, others idle
        for d in components:
            did = id(d)
            if did in final_assigned:
                fid = final_assigned[did]
                group = f"protecting {fid}"
                environment.assign_group(d, group if group in group_ids else idle_group)
            else:
                environment.assign_group(d, idle_group)