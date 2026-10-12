from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Keep previous explicit assignments to encourage stickiness across steps.
        # Keyed by component object (assumed stable across calls).
        self.last_assignments = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance_to_field(self, comp, field):
        cx, cy = self._field_center(field)
        return hypot(comp.location.x - cx, comp.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group(field_id):
            return f"protecting {field_id}"

        total = len(components)
        if total == 0:
            return

        min_protectors = ceil(total / 2)  # at least half protecting

        # Select fields with positive threat, sorted by descending threat
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        field_by_id = {f.id: f for f in fields}

        # Categorize drones by observed state
        protectors_by_field = defaultdict(list)
        movers_by_field = defaultdict(list)
        idle = []
        others = []
        for c in components:
            if c.state == "protecting" and c.target_id is not None:
                protectors_by_field[c.target_id].append(c)
            elif c.state == "moving_to_field" and c.target_id is not None:
                movers_by_field[c.target_id].append(c)
            elif c.state == "idle":
                idle.append(c)
            else:
                others.append(c)

        assigned = {}  # comp -> group string (we will fill this)

        # Helper to choose candidates for a field with strong stickiness preference
        def candidates_for_field(field, consider_protectors_of_others=True):
            fid = field.id
            dist_cache = {}
            def dist(c):
                if c not in dist_cache:
                    dist_cache[c] = self._distance_to_field(c, field)
                return dist_cache[c]

            cand = []
            for c in components:
                if c in assigned:
                    continue
                # priority based on previous assignment and current observable state
                last = self.last_assignments.get(c)
                if last == protecting_group(fid):
                    priority = 0
                elif c.state == "protecting" and c.target_id == fid:
                    priority = 1
                elif c.state == "moving_to_field" and c.target_id == fid:
                    priority = 2
                elif c.state == "idle":
                    priority = 3
                elif c.state == "moving_to_field":
                    priority = 4
                elif c.state == "protecting":
                    # protector of another field
                    priority = 5 if consider_protectors_of_others else 9
                else:
                    priority = 6
                # Exclude protectors of others if not allowed
                if priority == 9:
                    continue
                cand.append((priority, dist(c), c))
            cand.sort(key=lambda x: (x[0], x[1]))
            return [c for (_, _, c) in cand]

        # Preserve existing protectors up to required number to reduce churn
        for f in fields:
            req = int(f.drones_for_full_protection)
            cur = protectors_by_field.get(f.id, [])
            if cur:
                keep = cur[:req]
                for c in keep:
                    if c not in assigned:
                        assigned[c] = protecting_group(f.id)

        # Ensure top field is fully protected using closest/sticky drones.
        if fields:
            top = fields[0]
            top_group = protecting_group(top.id)
            if top_group in group_ids:
                required = int(top.drones_for_full_protection)
                already = sum(1 for c, g in assigned.items() if g == top_group)
                need = max(0, required - already)
                if need > 0:
                    cands = candidates_for_field(top, consider_protectors_of_others=True)
                    # pick the needed drones in candidate order
                    for c in cands:
                        if need <= 0:
                            break
                        if c in assigned:
                            continue
                        # avoid stealing from higher-threat fields implicitly because candidates order prefers non-protectors first
                        assigned[c] = top_group
                        need -= 1
                # Trim any over-assignment (defensive)
                assigned_top = [c for c, g in assigned.items() if g == top_group]
                if len(assigned_top) > required:
                    # keep previously assigned protectors first
                    orig = [c for c in protectors_by_field.get(top.id, []) if c in assigned_top]
                    keep = set(orig[:required])
                    if len(keep) < required:
                        others_sorted = sorted([c for c in assigned_top if c not in keep],
                                               key=lambda comp: self._distance_to_field(comp, top))
                        for c in others_sorted:
                            if len(keep) >= required:
                                break
                            keep.add(c)
                    for c in assigned_top:
                        if c not in keep:
                            del assigned[c]

        # Try to fully protect additional fields in descending threat order but only using unassigned non-protectors
        for f in fields[1:]:
            group = protecting_group(f.id)
            if group not in group_ids:
                continue
            req = int(f.drones_for_full_protection)
            already = sum(1 for c, g in assigned.items() if g == group)
            need = max(0, req - already)
            if need == 0:
                continue
            # available unassigned non-protectors
            unassigned_non_protectors = [c for c in components if c not in assigned and not (c.state == "protecting" and c.target_id is not None)]
            if len(unassigned_non_protectors) < need:
                # Not enough spare drones to fully protect this field without stealing -> skip
                continue
            # pick candidates for this field but do not allow stealing protectors of other fields in this stage
            cands = candidates_for_field(f, consider_protectors_of_others=False)
            picked = 0
            for c in cands:
                if picked >= need:
                    break
                if c in assigned:
                    continue
                assigned[c] = group
                picked += 1

        # Count currently protecting
        protecting_count = sum(1 for g in assigned.values() if g != "idle")

        # If fewer than half are protecting, try to use remaining unassigned drones (idle/movers) to reach half,
        # preferring highest-threat fields and preserving existing protectors.
        if protecting_count < min_protectors:
            need_more = min_protectors - protecting_count
            # First fill vacant capacity (not exceeding required) in fields by using unassigned non-protectors
            for f in fields:
                if need_more <= 0:
                    break
                group = protecting_group(f.id)
                if group not in group_ids:
                    continue
                req = int(f.drones_for_full_protection)
                already = sum(1 for c, g in assigned.items() if g == group)
                free_slots = max(0, req - already)
                if free_slots <= 0:
                    continue
                # pick candidates but do not steal protectors of other fields
                cands = candidates_for_field(f, consider_protectors_of_others=False)
                for c in cands:
                    if need_more <= 0 or free_slots <= 0:
                        break
                    if c in assigned:
                        continue
                    assigned[c] = group
                    need_more -= 1
                    free_slots -= 1

            # If still short, reluctantly steal the minimum required protectors from the least valuable fields
            if need_more > 0:
                # Build list of candidate protectors to steal: protectors not assigned yet(sorted by (value, -distance_to_own_center))
                steal_pool = []
                for other in fields:
                    req = int(other.drones_for_full_protection)
                    # current protectors (observable) that are not yet assigned
                    for c in protectors_by_field.get(other.id, []):
                        if c in assigned:
                            continue
                        # value metric: lower threat per required drone -> less costly to steal from
                        value = other.threat_level / max(1, req)
                        # distance from drone to its own field center (farther -> better candidate to steal)
                        center = self._field_center(other)
                        dist_to_own = hypot(c.location.x - center[0], c.location.y - center[1])
                        steal_pool.append((value, -dist_to_own, other.threat_level, other.id, c))
                # sort ascending by value, then prefer far-from-center (descending dist -> we used negative)
                steal_pool.sort(key=lambda x: (x[0], x[1], -x[2]))
                # For each candidate protector, move them to the highest-threat field that still has capacity (or top field)
                for val, negdist, oth_threat, orig_field_id, c in steal_pool:
                    if need_more <= 0:
                        break
                    # find best target field (highest threat) that hasn't reached requirement
                    for target in fields:
                        tgt_group = protecting_group(target.id)
                        if tgt_group not in group_ids:
                            continue
                        req_t = int(target.drones_for_full_protection)
                        already_t = sum(1 for comp, g in assigned.items() if g == tgt_group)
                        if already_t >= req_t:
                            continue
                        # avoid moving a protector back to its own field
                        if orig_field_id == target.id:
                            continue
                        # avoid stealing from a higher-threat field to reinforce a lower-threat one
                        orig_field = field_by_id.get(orig_field_id)
                        if orig_field is not None and orig_field.threat_level > target.threat_level:
                            continue
                        # assign
                        assigned[c] = tgt_group
                        need_more -= 1
                        break

        # After all, any unassigned drones become idle
        for c in components:
            if c not in assigned:
                assigned[c] = "idle"

        # Explicitly assign every drone using environment.assign_group
        for comp, group in assigned.items():
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)

        # Update last_assignments for stickiness in next step
        self.last_assignments = dict(assigned)