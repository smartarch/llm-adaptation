from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, comp, field):
        cx, cy = self._field_center(field)
        dx = comp.location.x - cx
        dy = comp.location.y - cy
        return math.hypot(dx, dy)

    def _field_area(self, field):
        w = max(0.0, field.right - field.left)
        h = max(0.0, field.bottom - field.top)
        area = w * h
        return max(1.0, area)

    def assign_drones(self, components, environment, group_ids, step: int):
        comps = list(components)
        # Deterministic index for tie-breaking
        comp_index = {c: i for i, c in enumerate(comps)}

        # Helpers to create group name
        def protect_group(field_id):
            return f"protecting {field_id}"

        # Collect threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # no threats -> idle all
            for c in comps:
                environment.assign_group(c, "idle")
            return

        # choose top field (highest threat, tie by id)
        max_threat = max(f.threat_level for f in fields)
        top_candidates = [f for f in fields if f.threat_level == max_threat]
        top_field = sorted(top_candidates, key=lambda f: f.id)[0]
        top_group = protect_group(top_field.id)
        if top_group not in group_ids:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        # categorize drones
        locked_protecting = []   # drones currently protecting (we prefer not to move them)
        idle_drones = []
        moving_drones = []
        for c in comps:
            state = getattr(c, "state", None)
            if state == "protecting":
                locked_protecting.append(c)
            elif state == "idle":
                idle_drones.append(c)
            elif state == "moving_to_field":
                moving_drones.append(c)
            else:
                idle_drones.append(c)

        # Count locked protecting per field
        locked_count = {}
        for f in environment.fields:
            locked_count[f.id] = 0
        for c in locked_protecting:
            tid = getattr(c, "target_id", None)
            if tid is not None:
                locked_count[tid] = locked_count.get(tid, 0) + 1

        # Start building assignment map; we must assign every component explicitly
        assignment = {}

        # First: keep locked protecting drones at their fields (do not move them)
        for c in locked_protecting:
            tid = getattr(c, "target_id", None)
            if tid is None:
                # ambiguous, keep idle to be safe
                assignment[c] = "idle"
            else:
                grp = protect_group(tid) if protect_group(tid) in group_ids else "idle"
                assignment[c] = grp

        # Next: ensure top field is fully protected if possible
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        currently_locked_top = locked_count.get(top_field.id, 0)
        # also count non-locked but already moving to top_field (they are in moving_drones with target_id)
        moving_to_top = [c for c in moving_drones if getattr(c, "target_id", None) == top_field.id]
        # treat moving_to_top as available but prefer not to reassign them away
        # They are already en-route to top, so keep them in top assignment
        current_top_sum = currently_locked_top + len(moving_to_top)

        # Assign moving-to-top drones to top in assignment (they should remain)
        for c in moving_to_top:
            assignment[c] = top_group

        # Build pool of free idle drones (sorted deterministically)
        idle_drones_sorted = sorted(idle_drones, key=lambda c: (self._distance(c, top_field), c.location.x, c.location.y, comp_index[c]))

        # Need drones to reach required_top, prefer locked and moving already counted above
        need_top = max(0, required_top - current_top_sum)
        used_idle_for_top = []
        if need_top > 0 and idle_drones_sorted:
            take = idle_drones_sorted[:need_top]
            for c in take:
                assignment[c] = top_group
            used_idle_for_top = take
            # remove them from idle pool
            idle_drones_sorted = [c for c in idle_drones_sorted if c not in take]
            need_top = max(0, need_top - len(take))

        # If still need and we are willing to reassign some moving drones (but not locked protecting drones)
        if need_top > 0 and moving_drones:
            # consider moving drones that target other fields with lower threat than top_field
            candidates = []
            for c in moving_drones:
                if c in moving_to_top:
                    continue
                tgt_id = getattr(c, "target_id", None)
                tgt_field = next((f for f in environment.fields if f.id == tgt_id), None)
                if tgt_field is None:
                    # strange, consider this drone as candidate (no target)
                    candidates.append((0.0, 0.0, comp_index[c], c))
                    continue
                # only consider reassigning if target's threat is lower than top_field
                if tgt_field.threat_level < top_field.threat_level:
                    # compute penalty = extra travel distance to go to top instead of original target
                    dist_to_top = self._distance(c, top_field)
                    dist_to_orig = self._distance(c, tgt_field)
                    extra_cost = max(0.0, dist_to_top - dist_to_orig)
                    # smaller extra_cost is better
                    candidates.append((extra_cost, tgt_field.threat_level, comp_index[c], c))
            # sort by (extra_cost asc, original target threat asc, tie index)
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            take_reassign = [t[3] for t in candidates[:need_top]]
            for c in take_reassign:
                assignment[c] = top_group
            need_top = max(0, need_top - len(take_reassign))

        # If cannot fully secure top field, we've still assigned what we could: locked + moving_to_top + used idle + reassigned moving
        # Now update pools of idle and moving not yet assigned
        # Recompute idle pool list for later steps
        idle_pool = [c for c in idle_drones_sorted if c not in assignment]
        moving_pool = [c for c in moving_drones if c not in assignment]

        # For other fields: compute extra drones needed beyond locked protecting (locked contributions remain)
        other_fields = [f for f in environment.fields if f.id != top_field.id and getattr(f, "threat_level", 0) > 0 and protect_group(f.id) in group_ids]
        # Precompute values
        field_infos = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            locked = locked_count.get(f.id, 0)
            # Also count moving drones already moving to this field that we didn't reassign; include them as contributing
            moving_to_field = sum(1 for c in moving_pool if getattr(c, "target_id", None) == f.id)
            already = locked + moving_to_field
            extra_needed = max(0, req - already)
            value = f.threat_level * self._field_area(f)
            # average distance of closest extra_needed idle drones to field (estimate)
            if extra_needed <= 0:
                avg_dist = 0.0
            else:
                dists = sorted(self._distance(c, f) for c in idle_pool)
                if dists:
                    take = dists[:extra_needed] if len(dists) >= extra_needed else dists
                    avg_dist = sum(take) / len(take)
                else:
                    avg_dist = float('inf')
            field_infos.append({
                "field": f,
                "req": req,
                "already": already,
                "extra": extra_needed,
                "value": value,
                "avg_dist": avg_dist
            })

        # Sort candidate fields by (value_per_extra / (1+avg_dist)) desc, tie by field id
        field_infos.sort(key=lambda x: (- (x["value"] / max(1, x["extra"])) / (1.0 + (x["avg_dist"] if x["avg_dist"] != float('inf') else 1e6)), x["field"].id))

        # Greedily fully protect fields using idle_pool (do not reassign protecting drones)
        # always pick closest idle drones to fill a field
        idle_pool.sort(key=lambda c: (c.location.x, c.location.y, comp_index[c]))
        for info in field_infos:
            f = info["field"]
            extra = info["extra"]
            if extra <= 0:
                # already has enough (locked + moving), assign contributors from moving_pool to that field in assignment
                for c in list(moving_pool):
                    if getattr(c, "target_id", None) == f.id:
                        assignment[c] = protect_group(f.id)
                        moving_pool.remove(c)
                continue
            if extra <= len(idle_pool):
                # pick closest idle drones to this field
                idle_sorted_by_dist = sorted(idle_pool, key=lambda c: (self._distance(c, f), comp_index[c]))
                chosen = idle_sorted_by_dist[:extra]
                for c in chosen:
                    assignment[c] = protect_group(f.id)
                    idle_pool.remove(c)
            else:
                # not enough idle drones to fully protect; skip full protection
                continue

        # After filling as many full protections as possible, assign remaining idle drones individually
        remaining_idle = list(idle_pool)
        if remaining_idle:
            # candidate fields include all threatened fields (excluding top) with a protecting group
            candidate_fields = [f for f in environment.fields if f.id != top_field.id and getattr(f, "threat_level", 0) > 0 and protect_group(f.id) in group_ids]
            if candidate_fields:
                for c in remaining_idle:
                    # pick best field for this drone by key: (-threat/req, distance, field id)
                    best_f = None
                    best_key = None
                    for f in candidate_fields:
                        req = max(1, int(getattr(f, "drones_for_full_protection", 1)))
                        key = (- (f.threat_level / req), self._distance(c, f), f.id)
                        if best_key is None or key < best_key:
                            best_key = key
                            best_f = f
                    if best_f is not None:
                        assignment[c] = protect_group(best_f.id)
                    else:
                        assignment[c] = "idle"
            else:
                for c in remaining_idle:
                    assignment[c] = "idle"

        # For any moving drones not yet assigned (that we didn't reassign), keep them targeting their current target
        for c in moving_pool:
            tgt = getattr(c, "target_id", None)
            if tgt is not None and protect_group(tgt) in group_ids:
                assignment[c] = protect_group(tgt)
            else:
                # if their target group not available, make them idle
                assignment[c] = "idle"

        # Ensure top-field contributors that were moving_to_top were assigned earlier; but if some weren't, enforce them now
        # (assignment map may already have them). Also ensure any locked_protecting already assigned.
        # Finally, assign any component not explicitly assigned to idle
        for c in comps:
            grp = assignment.get(c, None)
            if grp is None:
                assignment[c] = "idle"

        # Perform assignments explicitly for every component
        for c in comps:
            environment.assign_group(c, assignment[c])