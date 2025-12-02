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
        # Basic data
        comps = list(components)
        comp_index = {comp: i for i, comp in enumerate(comps)}

        # Threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        # Choose top field (highest threat, tie by id)
        max_threat = max(f.threat_level for f in fields)
        top_candidates = [f for f in fields if f.threat_level == max_threat]
        top_field = sorted(top_candidates, key=lambda f: f.id)[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Helper: which comps are currently targeting a field
        def currently_targeting(field, comp):
            return getattr(comp, "target_id", None) == field.id and getattr(comp, "state", None) in ("moving_to_field", "protecting")

        # Assignment map and pools
        assignment = {}
        remaining = set(comps)

        # Count currently targeting top field
        currently_top = [c for c in comps if currently_targeting(top_field, c)]
        if len(currently_top) >= required_top:
            # already fully protected; keep those drones there
            for c in currently_top:
                assignment[c] = top_group
                if c in remaining:
                    remaining.remove(c)
        else:
            # Need to select required_top drones; prefer those already targeting top, then pick closest from all drones
            # Build list of (priority, distance, tie-break index, comp)
            lst = []
            for c in comps:
                # prefer ones already targeting top: priority 0, else 1
                prio = 0 if currently_targeting(top_field, c) else 1
                dist = self._distance(c, top_field)
                lst.append((prio, dist, comp_index[c], c))
            lst.sort()
            chosen = [item[3] for item in lst[:required_top]]
            for c in chosen:
                assignment[c] = top_group
                if c in remaining:
                    remaining.remove(c)

        # Now we have remaining drones (set). Convert to list for ordering
        remaining = list(remaining)

        # For other fields, compute how many they already have among remaining drones (we preserved top)
        other_fields = [f for f in fields if f.id != top_field.id and f"protecting {f.id}" in group_ids]
        # Build candidate info: (field, required, current_count, extra_needed, value, avg_dist_of_needed)
        candidates = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            # current count among remaining drones that are already targeting this field
            curr = sum(1 for c in remaining if currently_targeting(f, c))
            extra_needed = max(0, req - curr)
            value = f.threat_level * self._field_area(f)
            # estimate avg distance of extra_needed closest drones (if extra_needed==0 -> 0)
            if extra_needed == 0:
                avg_dist = 0.0
            else:
                dists = sorted(self._distance(c, f) for c in remaining)
                # if not enough drones, use average of all remaining as estimate
                take = dists[:extra_needed] if len(dists) >= extra_needed else dists + [max(dists) if dists else 1.0] * (extra_needed - len(dists))
                avg_dist = sum(take) / len(take) if take else 1.0
            candidates.append({
                "field": f,
                "req": req,
                "curr": curr,
                "extra": extra_needed,
                "value": value,
                "avg_dist": avg_dist
            })

        # Sort candidates by score = (value / max(1, extra)) / (1 + avg_dist)
        # So we prefer fields with high value per needed drone and close proximity
        candidates.sort(key=lambda x: (
            - (x["value"] / max(1, x["extra"])) / (1.0 + x["avg_dist"]),
            x["field"].id
        ))

        # Greedily fully protect fields in this order using closest remaining drones
        remaining_pool = list(remaining)
        # deterministic ordering
        remaining_pool.sort(key=lambda c: (c.location.x, c.location.y, comp_index[c]))
        for info in candidates:
            f = info["field"]
            extra = info["extra"]
            if extra <= 0:
                # already fully protected by remaining drones; assign those
                for c in list(remaining_pool):
                    if currently_targeting(f, c):
                        assignment[c] = f"protecting {f.id}"
                        remaining_pool.remove(c)
            else:
                if extra <= len(remaining_pool):
                    # pick closest extra drones to field
                    sorted_by_dist = sorted(remaining_pool, key=lambda c: (self._distance(c, f), comp_index[c]))
                    to_assign = sorted_by_dist[:extra]
                    for c in to_assign:
                        assignment[c] = f"protecting {f.id}"
                        remaining_pool.remove(c)
                else:
                    # not enough drones to fully protect; skip for now
                    continue

        # Any remaining drones: assign individually by marginal benefit per drone (value/k adjusted by distance)
        leftovers = list(remaining_pool)
        if leftovers:
            # precompute basic data for candidate fields (including ones we may have left partially unprotected)
            cand_map = {}
            for f in other_fields:
                req = int(getattr(f, "drones_for_full_protection", 0))
                if req <= 0:
                    continue
                # current assigned count among assignment (excluding top)
                assigned_count = sum(1 for c, g in assignment.items() if g == f"protecting {f.id}")
                cand_map[f.id] = {
                    "field": f,
                    "req": req,
                    "assigned": assigned_count,
                    "value": f.threat_level * self._field_area(f)
                }
            # also consider top_field for possible extra drones (though not necessary) - we will not add extras to top
            for c in leftovers:
                best_f = None
                best_score = 0.0
                best_key = None
                for info in cand_map.values():
                    f = info["field"]
                    req = info["req"]
                    assigned = info["assigned"]
                    if assigned >= req:
                        # no marginal benefit
                        continue
                    # marginal benefit approximated linearly but reduced by closeness to full:
                    # marginal = (value / req) * (1 - assigned/req)
                    marginal = (info["value"] / req) * (1.0 - (assigned / req))
                    dist = self._distance(c, f)
                    # score = marginal / (1 + dist)
                    score = marginal / (1.0 + dist)
                    key = (-score, dist, f.id)
                    if best_f is None or key < best_key:
                        best_key = key
                        best_f = f
                        best_score = score
                if best_f is not None and best_score > 1e-9:
                    assignment[c] = f"protecting {best_f.id}"
                    cand_map[best_f.id]["assigned"] += 1
                else:
                    assignment[c] = "idle"

        # Finally ensure all components have explicit assignment
        for c in comps:
            g = assignment.get(c, "idle")
            environment.assign_group(c, g)