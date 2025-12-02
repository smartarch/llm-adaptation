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

        # Current protection counts per field
        current_by_field = {}
        for c in components:
            if getattr(c, 'state', None) == 'protecting':
                fid = getattr(c, 'target_id', None)
                if fid is not None:
                    current_by_field[fid] = current_by_field.get(fid, 0) + 1

        # Fields that are already fully protected
        fully_protected = set()
        for f in threat_fields:
            current = current_by_field.get(f.id, 0)
            if current >= getattr(f, 'drones_for_full_protection', 0) and current > 0:
                fully_protected.add(f.id)

        # Pool of drones we can reallocate (exclude those currently protecting a threatened field)
        pool = []
        for d in components:
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) in threat_ids:
                continue
            pool.append(d)

        plan_assignments = {}

        # Helper: number of additional drones needed for a field
        def needed_for_field(fid):
            f = next((ff for ff in threat_fields if ff.id == fid), None)
            if f is None:
                return 0
            current = current_by_field.get(fid, 0)
            return max(0, getattr(f, 'drones_for_full_protection', 0) - current)

        # Sort threat fields by (needed ascending, threat_level descending)
        threat_sorted = sorted(threat_fields, key=lambda f: (needed_for_field(f.id), -getattr(f, 'threat_level', 0)))

        # Allocate drones to fields in need
        for f in threat_sorted:
            fid = f.id
            if fid in fully_protected:
                continue
            need = needed_for_field(fid)
            if need <= 0:
                fully_protected.add(fid)
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
                current_by_field[fid] = current_by_field.get(fid, 0) + 1
            if take > 0:
                fully_protected.add(fid)

        # Final re-assignment:
        for d in components:
            if d in plan_assignments:
                environment.assign_group(d, f"protecting {plan_assignments[d]}")
            else:
                if getattr(d, 'state', None) == 'protecting':
                    fid = getattr(d, 'target_id', None)
                    if fid in fully_protected:
                        environment.assign_group(d, f"protecting {fid}")
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")