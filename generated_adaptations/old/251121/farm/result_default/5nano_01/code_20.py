from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Precompute field centers
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        threat_ids = {f.id for f in threat_fields}

        # Current protection counts per field (only threat fields)
        current_by_field = {}
        for c in components:
            if getattr(c, 'state', None) == 'protecting':
                fid = getattr(c, 'target_id', None)
                if fid in threat_ids:
                    current_by_field[fid] = current_by_field.get(fid, 0) + 1

        # Remaining protection needed per field
        remaining = {}
        for f in threat_fields:
            N = getattr(f, 'drones_for_full_protection', 0)
            if N <= 0:
                remaining[f.id] = 0
            else:
                remaining[f.id] = max(0, N - current_by_field.get(f.id, 0))

        # Determine which fields are already fully protected
        fully_protected = {f.id for f in threat_fields if remaining.get(f.id, 0) == 0 and current_by_field.get(f.id, 0) > 0}

        # Pool: drones we can reallocate (exclude locked drones protecting fully protected fields)
        pool = []
        for d in components:
            if getattr(d, 'state', None) == 'protecting':
                target = getattr(d, 'target_id', None)
                if target in threat_ids and target in fully_protected:
                    # This drone is protecting a field that is already fully protected -> lock it
                    continue
            pool.append(d)

        plan_assignments = {}  # drone -> field_id
        plan_fields = set(fully_protected)  # fields we will consider protected (expanded as we plan)

        # Greedy plan: maximize number of fully protected fields by filling from those needing the fewest drones
        # Build list of fields that still need protection
        needing = [f for f in threat_fields if remaining.get(f.id, 0) > 0]
        needing.sort(key=lambda f: (remaining.get(f.id, 0), -getattr(f, 'threat_level', 0)))

        # Allocate drones from the pool to each needed field
        for f in needing:
            fid = f.id
            need = remaining.get(fid, 0)
            if need <= 0:
                plan_fields.add(fid)
                continue

            cx, cy = centers[fid]

            # Build distance-sorted candidate drones from the pool
            candidates = []
            for d in pool:
                loc = getattr(d, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0) - cx
                    dy = getattr(loc, 'y', 0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])
            take = min(need, len(candidates))
            for i in range(take):
                drone = candidates[i][1]
                plan_assignments[drone] = fid
                pool.remove(drone)
                remaining[fid] = max(0, remaining.get(fid, 0) - 1)
            if remaining.get(fid, 0) == 0:
                plan_fields.add(fid)

        # Apply assignments
        plan_field_ids = set(plan_fields)  # fields we plan to protect (including those fully protected)

        for d, fid in plan_assignments.items():
            environment.assign_group(d, f"protecting {fid}")

        # For drones not assigned in plan, preserve protection if it's part of the plan; otherwise idle
        for d in components:
            if d in plan_assignments:
                continue
            if getattr(d, 'state', None) == 'protecting':
                fid = getattr(d, 'target_id', None)
                if fid in plan_field_ids:
                    environment.assign_group(d, f"protecting {fid}")
                else:
                    environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, "idle")