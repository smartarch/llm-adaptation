from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with any threat
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Precompute field centers
        field_centers = {}
        for f in threat_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Current protection status per field
        current_protecting_by_field = {}
        protect_drones_by_field = {}
        for c in components:
            if getattr(c, 'state', None) == 'protecting':
                fid = getattr(c, 'target_id', None)
                if fid is not None:
                    current_protecting_by_field[fid] = current_protecting_by_field.get(fid, 0) + 1
                    protect_drones_by_field.setdefault(fid, []).append(c)

        # Sort threat fields by threat level (high to low)
        threat_fields_sorted = sorted(threat_fields, key=lambda f: getattr(f, 'threat_level', 0), reverse=True)

        plan_fields = set()          # fields we plan to protect this step
        plan_assignments = {}          # drone -> field_id for newly allocated drones

        # Step 1: mark already fully protected fields
        for f in threat_fields_sorted:
            current = current_protecting_by_field.get(f.id, 0)
            if current >= getattr(f, 'drones_for_full_protection', 0) and current > 0:
                plan_fields.add(f.id)

        # Step 2: greedily try to fully protect remaining high-threat fields
        for f in threat_fields_sorted:
            if f.id in plan_fields:
                continue
            current = current_protecting_by_field.get(f.id, 0)
            needed = max(0, getattr(f, 'drones_for_full_protection', 0) - current)
            if needed <= 0:
                plan_fields.add(f.id)
                continue

            cx, cy = field_centers[f.id]

            # Candidate drones: not currently protecting this field
            candidates = []
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == f.id:
                    continue
                loc = getattr(d, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0) - cx
                    dy = getattr(loc, 'y', 0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])
            take = min(needed, len(candidates))
            for i in range(take):
                drone = candidates[i][1]
                plan_assignments[drone] = f.id
                current_protecting_by_field[f.id] = current_protecting_by_field.get(f.id, 0) + 1
                plan_fields.add(f.id)

        # Final re-assignment:
        # - Drones allocated in plan_assignments -> protecting {field_id}
        # - Drones currently protecting a field in plan_fields -> keep protecting that field
        # - All others -> idle
        for c in components:
            if c in plan_assignments:
                environment.assign_group(c, f"protecting {plan_assignments[c]}")
            else:
                # If this drone is currently protecting some field that's in the plan, keep it on that field
                if getattr(c, 'state', None) == 'protecting':
                    fid = getattr(c, 'target_id', None)
                    if fid in plan_fields:
                        environment.assign_group(c, f"protecting {fid}")
                    else:
                        environment.assign_group(c, "idle")
                else:
                    environment.assign_group(c, "idle")