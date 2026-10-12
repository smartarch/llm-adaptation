from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance_to_field(self, comp, field):
        cx, cy = self._field_center(field)
        return hypot(comp.location.x - cx, comp.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group(field_id):
            return f"protecting {field_id}"

        total_drones = len(components)
        if total_drones == 0:
            return

        # At least half drones should be protecting (rounded up)
        min_protectors = ceil(total_drones / 2)

        # Consider only fields with threat>0 (group_ids will include these protect groups)
        fields = [f for f in environment.fields if f.threat_level > 0]
        # Sort by descending threat (primary) then id (stable)
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        field_by_id = {f.id: f for f in fields}

        # Categorize drones based on observable states
        protectors_by_field = defaultdict(list)
        movers_by_field = defaultdict(list)
        idle_drones = []
        other_drones = []  # drones that are in other/unknown states

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

        def mark_assigned(comp, group_name):
            assigned[comp] = group_name

        # Candidate ordering for a target field:
        # 0: protectors already on that field (keep)
        # 1: movers targeting that field
        # 2: idle drones
        # 3: movers to other fields (sorted by distance to this field)
        # 4: protectors of other fields (only if necessary), prefer steal from lowest-threat fields and those far from their field center
        def gather_candidates(field):
            fid = field.id
            candidates = []
            # keep existing protectors first
            for c in protectors_by_field.get(fid, []):
                if c not in assigned:
                    candidates.append((0, self._distance_to_field(c, field), c))
            # movers to this field
            for c in movers_by_field.get(fid, []):
                if c not in assigned:
                    candidates.append((1, self._distance_to_field(c, field), c))
            # idle drones
            for c in idle_drones:
                if c not in assigned:
                    candidates.append((2, self._distance_to_field(c, field), c))
            # movers to other fields
            for tgt, movers in movers_by_field.items():
                if tgt == fid:
                    continue
                for c in movers:
                    if c not in assigned:
                        candidates.append((3, self._distance_to_field(c, field), c))
            # protectors of other fields: only include as last resort, sort by (their field threat asc, distance from their field center desc)
            protector_candidates = []
            for other_f in fields:
                if other_f.id == fid:
                    continue
                for c in protectors_by_field.get(other_f.id, []):
                    if c in assigned:
                        continue
                    # distance from this drone to its current field center (we prefer those far from their field -> less efficient there)
                    other_center = self._field_center(other_f)
                    dist_to_own_center = hypot(c.location.x - other_center[0], c.location.y - other_center[1])
                    protector_candidates.append((other_f.threat_level, -dist_to_own_center, self._distance_to_field(c, field), c))
            # sort: prefer stealing from lowest-threat fields and among them those farthest from their field center, then closer to target
            protector_candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            for threat_level, negdist, dist_to_target, c in protector_candidates:
                candidates.append((4, dist_to_target, c))

            # finalize ordering by priority then distance-to-target
            candidates.sort(key=lambda x: (x[0], x[1]))
            ordered = []
            seen = set()
            for _, _, comp in candidates:
                if comp not in seen:
                    seen.add(comp)
                    ordered.append(comp)
            return ordered

        # Preserve existing protectors up to required number to reduce churn
        for f in fields:
            req = int(f.drones_for_full_protection)
            cur_prot = protectors_by_field.get(f.id, [])
            if cur_prot:
                keep = cur_prot[:req]
                for c in keep:
                    if c not in assigned:
                        mark_assigned(c, protecting_group(f.id))

        # Forcefully ensure the top threat field is fully protected using closest available drones,
        # without taking protectors from other fields unless absolutely necessary.
        if fields:
            top = fields[0]
            top_group = protecting_group(top.id)
            if top_group in group_ids:
                required = int(top.drones_for_full_protection)
                already = [c for c, g in assigned.items() if g == top_group]
                needed = max(0, required - len(already))
                if needed > 0:
                    candidates = gather_candidates(top)
                    # select in candidate order
                    for c in candidates:
                        if needed <= 0:
                            break
                        if c in assigned:
                            continue
                        # do not take protectors from other fields (priority 4) unless we have exhausted categories 0-3
                        # Since candidates are ordered, this automatically avoids stealing unless necessary.
                        mark_assigned(c, top_group)
                        needed -= 1
                # ensure not overprotecting
                assigned_to_top = [c for c, g in assigned.items() if g == top_group]
                if len(assigned_to_top) > required:
                    # keep original protectors first
                    orig = [c for c in protectors_by_field.get(top.id, []) if c in assigned_to_top]
                    keep = set(orig[:required])
                    if len(keep) < required:
                        others_sorted = sorted([c for c in assigned_to_top if c not in keep],
                                               key=lambda comp: self._distance_to_field(comp, top))
                        for c in others_sorted:
                            if len(keep) >= required:
                                break
                            keep.add(c)
                    for c in assigned_to_top:
                        if c not in keep:
                            del assigned[c]

        # Try to fully protect additional fields in threat order, but only if we can fill them using unassigned drones
        # (idle or movers or other unassigned) without stealing protectors from currently assigned protected fields.
        for f in fields[1:]:
            group_name = protecting_group(f.id)
            if group_name not in group_ids:
                continue
            required = int(f.drones_for_full_protection)
            already_assigned = sum(1 for c, g in assigned.items() if g == group_name)
            need = max(0, required - already_assigned)
            if need == 0:
                continue
            # count unassigned drones that are not currently protecting other fields (i.e., idle or movers to anywhere)
            unassigned = [c for c in components if c not in assigned]
            # Among unassigned, prefer those that are not protectors (they could be idle or movers)
            non_protector_unassigned = [c for c in unassigned if not (c.state == "protecting" and c.target_id is not None)]
            if len(non_protector_unassigned) < need:
                # Not enough spare drones to fully protect this field without taking protectors from others -> skip
                continue
            # gather candidates and pick needed drones (gather_candidates places protectors-of-others last, so we will pick from non-protector_unassigned first)
            candidates = gather_candidates(f)
            picked = 0
            for c in candidates:
                if picked >= need:
                    break
                if c in assigned:
                    continue
                # skip if it's a protector of other field (we avoid stealing in this stage)
                if c.state == "protecting" and c.target_id is not None and c.target_id != f.id:
                    continue
                mark_assigned(c, group_name)
                picked += 1

        # Count how many drones are protecting now
        protecting_count = sum(1 for g in assigned.values() if g != "idle")

        # If fewer than half are protecting, assign more drones until min_protectors satisfied.
        # Now we allow partial protection or stealing from lower-threat fields if necessary.
        if protecting_count < min_protectors:
            need_more = min_protectors - protecting_count
            # Fill remaining capacity by iterating fields in threat order and assigning available drones:
            for f in fields:
                if need_more <= 0:
                    break
                group_name = protecting_group(f.id)
                if group_name not in group_ids:
                    continue
                required = int(f.drones_for_full_protection)
                already_assigned = sum(1 for c, g in assigned.items() if g == group_name)
                free_slots = max(0, required - already_assigned)
                # We can assign up to free_slots without overprotecting
                # If free_slots == 0, consider partial (allow extra partial beyond required? specification: don't overprotect fields; so do not exceed required)
                if free_slots <= 0:
                    continue
                # choose candidates; now allow taking protectors from lower-threat fields if needed (gather_candidates orders them last)
                candidates = gather_candidates(f)
                for c in candidates:
                    if need_more <= 0 or free_slots <= 0:
                        break
                    if c in assigned:
                        continue
                    # Steal only if necessary: prefer not to steal from a field with higher threat than this field
                    if c.state == "protecting" and c.target_id is not None and c.target_id != f.id:
                        other_field = field_by_id.get(c.target_id)
                        if other_field and other_field.threat_level > f.threat_level:
                            # don't steal from a higher-threat field
                            continue
                    mark_assigned(c, group_name)
                    need_more -= 1
                    free_slots -= 1

            # If still not enough (rare), allow stealing from remaining protectors starting from the lowest-threat fields
            if need_more > 0:
                # list protectors of fields sorted by field threat ascending (lowest first), then distance to their own field ascending (prefer ones farther? we choose farthest to reduce local effect)
                protector_pool = []
                for other_f in fields:
                    for c in protectors_by_field.get(other_f.id, []):
                        if c in assigned:
                            continue
                        # compute attractiveness for stealing: first lower threat, then far from their field center (we prefer those far away)
                        other_center = self._field_center(other_f)
                        dist_to_own = hypot(c.location.x - other_center[0], c.location.y - other_center[1])
                        protector_pool.append((other_f.threat_level, -dist_to_own, c, other_f))
                protector_pool.sort(key=lambda x: (x[0], x[1]))  # low threat first, then farthest
                # assign these protectors to highest remaining-threat fields
                for threat_lvl, negdist, c, original_field in protector_pool:
                    if need_more <= 0:
                        break
                    # pick best field to move this protector to: the highest-threat field that still has capacity (or top field)
                    for target in fields:
                        tgt_group = protecting_group(target.id)
                        if tgt_group not in group_ids:
                            continue
                        required = int(target.drones_for_full_protection)
                        already_assigned = sum(1 for comp, g in assigned.items() if g == tgt_group)
                        if already_assigned >= required:
                            continue
                        # avoid moving protector back to its own field (it already protects it)
                        if c in protectors_by_field.get(target.id, []):
                            continue
                        # do not steal from a higher-threat field to a lower-threat one
                        if original_field.threat_level > target.threat_level:
                            continue
                        # assign and break
                        mark_assigned(c, tgt_group)
                        need_more -= 1
                        break

        # Finally, any remaining unassigned drones become idle
        for c in components:
            if c not in assigned:
                assigned[c] = "idle"

        # Explicitly assign every drone to its group
        for comp, group in assigned.items():
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)