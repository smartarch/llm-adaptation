from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0  # given in problem statement

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # store last explicit assignments for stickiness across steps
        self.last_assignments = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, a, b):
        return hypot(a.x - b.x, a.y - b.y)

    def _distance_to_field(self, comp, field):
        cx, cy = self._field_center(field)
        # comp.location has x and y
        return hypot(comp.location.x - cx, comp.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group(field_id):
            return f"protecting {field_id}"

        total_drones = len(components)
        if total_drones == 0:
            return

        min_protectors = ceil(total_drones / 2)

        # Fields with positive threat
        fields = [f for f in environment.fields if f.threat_level > 0]
        # Keep mapping for lookups
        field_by_id = {f.id: f for f in fields}
        # Always keep fields sorted by threat descending for tie-breaking
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Categorize drones by observed state/target
        protectors_by_field = defaultdict(list)
        movers_by_field = defaultdict(list)
        idle_drones = []
        other_drones = []
        for c in components:
            if c.state == "protecting" and c.target_id is not None:
                protectors_by_field[c.target_id].append(c)
            elif c.state == "moving_to_field" and c.target_id is not None:
                movers_by_field[c.target_id].append(c)
            elif c.state == "idle":
                idle_drones.append(c)
            else:
                other_drones.append(c)

        assigned = {}  # comp -> group_name

        # Compute arrival time estimate for a drone to a field
        def arrival_time(comp, field):
            # if already protecting that field => 0
            if comp.state == "protecting" and comp.target_id == field.id:
                return 0.0
            # estimate remaining distance to field center
            d = self._distance_to_field(comp, field)
            # simple travel time estimate: distance / speed
            return d / self.DRONE_SPEED

        # Candidate ordering for choosing drones for a field
        # lower priority tuple is preferred
        def candidate_priority(comp, field):
            # Prefer: last assignment to same field -> currently protecting that field -> moving to that field -> idle -> moving elsewhere -> protecting elsewhere -> others
            last = self.last_assignments.get(comp)
            p_last = 0 if last == protecting_group(field.id) else 1
            p_current_protect = 0 if (comp.state == "protecting" and comp.target_id == field.id) else 1
            p_moving_to = 0 if (comp.state == "moving_to_field" and comp.target_id == field.id) else 1
            p_idle = 0 if comp.state == "idle" else 1
            # Protector of other field penalty
            p_protector_other = 0 if (comp.state == "protecting" and comp.target_id is not None and comp.target_id != field.id) else 1
            # Moving to other fields is slightly better than being a protector elsewhere (we prefer reusing movers)
            p_moving_other = 0 if (comp.state == "moving_to_field" and comp.target_id is not None and comp.target_id != field.id) else 1
            # arrival time as tie-breaker
            at = arrival_time(comp, field)
            # Compose priority tuple
            # We order by:
            # 1) last assignment to this field (prefer keep)
            # 2) currently protecting this field
            # 3) currently moving to this field
            # 4) idle
            # 5) moving elsewhere
            # 6) protector of other fields (penalize)
            # 7) others
            return (p_last, p_current_protect, p_moving_to, p_idle, p_moving_other, p_protector_other, at)

        # Build candidate lists and compute a score per field based on best N drones arrival times
        field_candidates = {}
        for f in fields:
            group = protecting_group(f.id)
            if group not in group_ids:
                continue
            N = int(f.drones_for_full_protection)
            if N <= 0:
                continue
            # sort drones by candidate priority and arrival time for this field
            drones_sorted = sorted(components, key=lambda c: candidate_priority(c, f))
            # choose top N as hypothetical protection team
            team = drones_sorted[:N]
            avg_arrival = sum(arrival_time(c, f) for c in team) / float(len(team)) if team else float('inf')
            # Score: threat divided by cost. Add 1 to time to dampen very small denominators.
            score = f.threat_level / ((1.0 + avg_arrival) * max(1, N))
            field_candidates[f.id] = {
                "field": f,
                "N": N,
                "team": team,
                "avg_arrival": avg_arrival,
                "score": score,
            }

        # Always fully protect the single most threatened field first (hard requirement).
        if fields:
            top = fields[0]
            top_group = protecting_group(top.id)
            if top_group in group_ids:
                required = int(top.drones_for_full_protection)
                # Build ordered candidate list for top (using candidate priority)
                cand = sorted(components, key=lambda c: candidate_priority(c, top))
                picked = 0
                for c in cand:
                    if picked >= required:
                        break
                    if c in assigned:
                        continue
                    # prefer not to steal from protectors of higher-threat fields (candidate_priority already penalizes)
                    assigned[c] = top_group
                    picked += 1

        # Greedily allocate to other fields by descending score but only when we can fill them using unassigned non-protector drones
        # This reduces churn: don't steal protectors in this phase.
        remaining_field_infos = []
        for fid, info in field_candidates.items():
            if fid == (fields[0].id if fields else None):
                continue
            remaining_field_infos.append(info)
        remaining_field_infos.sort(key=lambda info: -info["score"])

        # Helper: count unassigned non-protector drones
        def unassigned_non_protectors():
            return [c for c in components if c not in assigned and not (c.state == "protecting" and c.target_id is not None)]

        for info in remaining_field_infos:
            f = info["field"]
            group = protecting_group(f.id)
            N = info["N"]
            already = sum(1 for c, g in assigned.items() if g == group)
            need = max(0, N - already)
            if need == 0:
                continue
            # Only fill if we can get 'need' drones from unassigned non-protectors
            available_non_prot = unassigned_non_protectors()
            if len(available_non_prot) < need:
                continue
            # pick candidates for this field but disallow stealing protectors
            cand = [c for c in sorted(components, key=lambda c: candidate_priority(c, f)) if c not in assigned]
            picked = 0
            for c in cand:
                if picked >= need:
                    break
                # skip protectors of other fields in this phase
                if c.state == "protecting" and c.target_id is not None and c.target_id != f.id:
                    continue
                assigned[c] = group
                picked += 1

        # Enforce at least half protecting. If too few, add drones preferentially to highest-value fields.
        current_protecting = sum(1 for g in assigned.values() if g != "idle")
        if current_protecting < min_protectors:
            needed_more = min_protectors - current_protecting
            # attempt to fill remaining capacity in fields by descending score
            candidates_fields = sorted(field_candidates.values(), key=lambda info: -info["score"])
            for info in candidates_fields:
                if needed_more <= 0:
                    break
                f = info["field"]
                group = protecting_group(f.id)
                N = info["N"]
                already = sum(1 for c, g in assigned.items() if g == group)
                free_slots = max(0, N - already)
                if free_slots <= 0:
                    continue
                # pick candidates (allow moving protectors if strictly necessary, but prefer non-protectors)
                cand = [c for c in sorted(components, key=lambda c: candidate_priority(c, f)) if c not in assigned]
                for c in cand:
                    if needed_more <= 0 or free_slots <= 0:
                        break
                    assigned[c] = group
                    needed_more -= 1
                    free_slots -= 1
            # If still not enough, reluctantly steal protectors from least valuable fields:
            if needed_more > 0:
                # Build list of available protectors we can steal (not already assigned)
                steal_pool = []
                for other in fields:
                    req = int(other.drones_for_full_protection)
                    cur_prots = protectors_by_field.get(other.id, [])
                    for c in cur_prots:
                        if c in assigned:
                            continue
                        # cost metric: value-per-drone = threat / req (lower is cheaper to steal)
                        val = other.threat_level / max(1, req)
                        # prefer those far from their own field center
                        center = self._field_center(other)
                        dist_to_own = hypot(c.location.x - center[0], c.location.y - center[1])
                        steal_pool.append((val, -dist_to_own, other, c))
                # sort so we steal from lowest value-per-drone first, and among them those farthest from their center
                steal_pool.sort(key=lambda x: (x[0], x[1]))
                # assign stolen protectors to highest-score fields that still have capacity
                targets_sorted = sorted(field_candidates.values(), key=lambda info: -info["score"])
                for val, negdist, orig_field, c in steal_pool:
                    if needed_more <= 0:
                        break
                    # pick best target to move this protector to (highest score with capacity)
                    for info in targets_sorted:
                        f = info["field"]
                        group = protecting_group(f.id)
                        if group not in group_ids:
                            continue
                        N = info["N"]
                        already = sum(1 for comp, g in assigned.items() if g == group)
                        if already >= N:
                            continue
                        # don't move back to its original field
                        if orig_field.id == f.id:
                            continue
                        # don't steal from higher-threat to support lower-threat (avoid making worse)
                        if orig_field.threat_level > f.threat_level:
                            continue
                        assigned[c] = group
                        needed_more -= 1
                        break

        # Any remaining unassigned drone becomes idle
        for c in components:
            if c not in assigned:
                assigned[c] = "idle"

        # Perform assignments (explicitly assign every drone)
        for comp, group in assigned.items():
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)

        # Update last_assignments to encourage stickiness next step
        self.last_assignments = dict(assigned)