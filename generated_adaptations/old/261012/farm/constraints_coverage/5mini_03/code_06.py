from math import hypot, ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Greedy allocation:
        1. Preserve drones already targeting fields (target_id).
        2. Score fields by threat_level / max(1, drones_for_full_protection).
        3. Greedily fully protect top-scoring fields using closest available drones.
        4. If still under the desired protecting threshold (>= half the fleet), do a second pass:
           - give one drone (partial protection) to the most threatened remaining fields
           - if still needed, allocate remaining drones to closest high-priority fields
        5. Remaining drones -> idle.
        """
        def assign_if_valid(comp, gid):
            if gid in group_ids:
                environment.assign_group(comp, gid)
            else:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                elif group_ids:
                    environment.assign_group(comp, group_ids[0])
                # else: nothing to do

        comps = list(components)
        total = len(comps)
        if total == 0:
            return

        # Candidate fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in comps:
                assign_if_valid(c, "idle")
            return

        # Field center helper
        def center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to(cx, cy, comp):
            lx = getattr(comp.location, "x", 0)
            ly = getattr(comp.location, "y", 0)
            return hypot(lx - cx, ly - cy)

        # Prepare scoring: prefer fields with high threat and low cost to fully protect
        scored_fields = []
        for f in fields:
            cost = int(getattr(f, "drones_for_full_protection", 0))
            if cost <= 0:
                cost = 1
            score = getattr(f, "threat_level", 0) / cost
            scored_fields.append((score, f))
        # Sort by score descending, tie-break by threat_level then id for determinism
        scored_fields.sort(key=lambda t: (t[0], getattr(t[1], "threat_level", 0), getattr(t[1], "id", "")), reverse=True)
        fields_by_score = [t[1] for t in scored_fields]

        # Track assignments by id(component)
        assigned_group_by_id = {}
        assigned_ids = set()

        # Pre-count drones already targeting fields (they are treated as committed)
        # Map field.id -> list of components already targeting it
        targeted_map = {}
        for c in comps:
            tid = c.target_id
            if tid is not None:
                targeted_map.setdefault(tid, []).append(c)

        # Helper: available drones pool (not yet assigned to a protecting group)
        def available_pool():
            return [c for c in comps if id(c) not in assigned_ids]

        # First pass: fully protect as many top-scoring fields as possible
        for f in fields_by_score:
            fid = f.id
            group_name = f"protecting {fid}"
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req < 0:
                req = 0
            # Count already committed (targeting this field)
            committed = [c for c in targeted_map.get(fid, []) if id(c) not in assigned_ids]
            for c in committed:
                cid = id(c)
                assigned_group_by_id[cid] = group_name
                assigned_ids.add(cid)
            committed_count = len(committed)
            need = max(0, req - committed_count)
            if need == 0:
                # Already fully protected by committed drones
                continue
            pool = available_pool()
            if not pool:
                break
            cx, cy = center(f)
            # pick closest 'need' drones
            pool_with_dist = sorted(((dist_to(cx, cy, c), c) for c in pool), key=lambda x: x[0])
            to_take = [c for (_, c) in pool_with_dist[:need]]
            for c in to_take:
                cid = id(c)
                assigned_group_by_id[cid] = group_name
                assigned_ids.add(cid)

        protecting_count = len(assigned_ids)
        target_protect = ceil(total / 2)

        # Second pass: give partial coverage (one drone) to remaining high-threat fields
        if protecting_count < target_protect:
            # Sort remaining fields by threat_level descending (prefer high threat)
            remaining_fields = sorted(
                [f for f in fields if f.id not in [fld.id for fld in fields_by_score[:0]]],
                key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
                reverse=True
            )
            # Actually we want all fields not yet fully protected; build set of already fully protected ids
            fully_protected_ids = set()
            # determine which fields are already fully protected in current assignments
            for f in fields:
                fid = f.id
                req = int(getattr(f, "drones_for_full_protection", 0))
                if req < 0:
                    req = 0
                assigned_for_field = sum(1 for c in comps if id(c) in assigned_ids and assigned_group_by_id.get(id(c)) == f"protecting {fid}")
                if assigned_for_field >= req:
                    fully_protected_ids.add(fid)
            # Fields left that are not fully protected, sorted by threat desc
            remaining_fields = sorted([f for f in fields if f.id not in fully_protected_ids],
                                      key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
                                      reverse=True)
            # Assign one drone to each such field (prefer drones already targeting it), until we reach target_protect
            for f in remaining_fields:
                if protecting_count >= target_protect:
                    break
                fid = f.id
                group_name = f"protecting {fid}"
                # try to use available drone that is already targeting this field first
                pool = available_pool()
                targeted_candidates = [c for c in pool if c.target_id == fid]
                if targeted_candidates:
                    # pick the closest among them to be stable
                    cx, cy = center(f)
                    targeted_candidates.sort(key=lambda c: dist_to(cx, cy, c))
                    c = targeted_candidates[0]
                    cid = id(c)
                    assigned_group_by_id[cid] = group_name
                    assigned_ids.add(cid)
                    protecting_count += 1
                    continue
                # otherwise pick closest available drone to field center
                pool = available_pool()
                if not pool:
                    break
                cx, cy = center(f)
                pool_with_dist = sorted(((dist_to(cx, cy, c), c) for c in pool), key=lambda x: x[0])
                c = pool_with_dist[0][1]
                cid = id(c)
                assigned_group_by_id[cid] = group_name
                assigned_ids.add(cid)
                protecting_count += 1

        # Third pass: if still under target_protect, assign remaining closest drones to highest-threat fields
        if protecting_count < target_protect:
            pool = available_pool()
            if pool:
                # Create list of fields sorted by threat (desc)
                fields_by_threat = sorted(fields, key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")), reverse=True)
                # For each available drone, assign it to the nearest high-threat field (cycling fields_by_threat)
                # until we reach target_protect
                pool_with_global_priority = []
                for c in pool:
                    # assign priority by min distance to any high-threat field weighted by field threat
                    best_score = None
                    best_f = None
                    for f in fields_by_threat:
                        cx, cy = center(f)
                        d = dist_to(cx, cy, c)
                        # smaller distance and higher threat -> better
                        score = d / max(1e-6, f.threat_level)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_f = f
                    if best_f is not None:
                        pool_with_global_priority.append((best_score, c, best_f))
                pool_with_global_priority.sort(key=lambda t: t[0])  # best first
                for (_, c, f) in pool_with_global_priority:
                    if protecting_count >= target_protect:
                        break
                    cid = id(c)
                    group_name = f"protecting {f.id}"
                    assigned_group_by_id[cid] = group_name
                    assigned_ids.add(cid)
                    protecting_count += 1

        # Final step: assign groups (those assigned to protecting groups get that, others idle)
        for c in comps:
            cid = id(c)
            if cid in assigned_group_by_id:
                assign_if_valid(c, assigned_group_by_id[cid])
            else:
                assign_if_valid(c, "idle")