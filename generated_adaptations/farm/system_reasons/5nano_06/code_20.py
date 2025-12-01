from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields
        fields = getattr(environment, 'fields', [])
        threatened = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        if not threatened:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort threats by threat level (desc)
        threat_sorted = sorted(threatened, key=lambda f: f.threat_level, reverse=True)
        top_field = threat_sorted[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If we can't assign to the top group, idle all
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper: map field_id -> field for quick access
        fields_by_id = {f.id: f for f in fields}

        # 3) Compute current protection counts
        current_prot = {fid: 0 for fid in fields_by_id}
        top_current = []
        for d in components:
            if getattr(d, 'state', None) == 'protecting':
                tid = getattr(d, 'target_id', None)
                if tid in current_prot:
                    current_prot[tid] += 1
                    if tid == top_field.id:
                        top_current.append(d)

        mapping = {}

        # 4) Step 1: Preserve existing top-field protectors
        for d in top_current:
            mapping[d] = top_group

        # Step 5) Initialize fully_protected_ids based on current protection
        fully_protected_ids = {
            fid for fid in fields_by_id
            if getattr(fields_by_id[fid], 'drones_for_full_protection', 0) > 0 and
               current_prot.get(fid, 0) >= getattr(fields_by_id[fid], 'drones_for_full_protection', 0)
        }

        # 6) Step 2: Fill top field to full protection
        current_top_count = len(top_current)
        max_full_top = min(getattr(top_field, 'drones_for_full_protection', 0), len(components))
        needed_top = max(0, max_full_top - current_top_count)

        if needed_top > 0:
            # Build candidate pool: prefer idle, then protecting fully-protected fields
            candidates = []
            top_cx = (top_field.left + top_field.right) / 2.0
            top_cy = (top_field.top + top_field.bottom) / 2.0

            for d in components:
                if d in mapping:
                    continue
                st = getattr(d, 'state', None)
                if st == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid not in fully_protected_ids:
                        # Do not pull from non-full fields
                        continue
                candidates.append(d)

            def dist_top(d):
                loc = getattr(d, 'location', None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, 'x', 0.0) - top_cx
                dy = getattr(loc, 'y', 0.0) - top_cy
                return (dx*dx + dy*dy) ** 0.5

            candidates.sort(key=dist_top)
            for i in range(min(needed_top, len(candidates))):
                d = candidates[i]
                mapping[d] = top_group
                current_top_count += 1
                current_prot[top_field.id] = current_prot.get(top_field.id, 0) + 1

            # Recompute fully_protected_ids after updates
            fully_protected_ids = {
                fid for fid in fields_by_id
                if getattr(fields_by_id[fid], 'drones_for_full_protection', 0) > 0 and
                   current_prot.get(fid, 0) >= getattr(fields_by_id[fid], 'drones_for_full_protection', 0)
            }

        # 7) Step 3: Spare capacity for other fields
        remaining = [d for d in components if d not in mapping]

        for f in threat_sorted[1:]:
            g_id = f"protecting {f.id}"
            if g_id not in group_ids:
                continue

            max_for_f = getattr(f, 'drones_for_full_protection', 0)
            current_f = current_prot.get(f.id, 0)
            needed_f = max(0, max_for_f - current_f)
            if needed_f <= 0:
                continue

            # Candidates: idle or protecting fully-protected fields
            candidates = []
            fcx = (f.left + f.right) / 2.0
            fcy = (f.top + f.bottom) / 2.0

            for d in remaining:
                st = getattr(d, 'state', None)
                if st == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid not in fully_protected_ids:
                        continue
                candidates.append(d)

            if not candidates:
                continue

            def dist_to_f(d):
                loc = getattr(d, 'location', None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, 'x', 0.0) - fcx
                dy = getattr(loc, 'y', 0.0) - fcy
                return (dx*dx + dy*dy) ** 0.5

            candidates.sort(key=dist_to_f)
            take = min(needed_f, len(candidates))

            for i in range(take):
                d = candidates[i]
                mapping[d] = g_id
                # Update counts
                if d.state == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid is not None:
                        current_prot[tid] = current_prot.get(tid, 0) - 1
                        if current_prot[tid] < 0:
                            current_prot[tid] = 0
                    # Now bump target field
                    current_prot[f.id] = current_prot.get(f.id, 0) + 1
                else:
                    # Idle moves to protecting f
                    current_prot[f.id] = current_prot.get(f.id, 0) + 1

            remaining = [d for d in remaining if d not in mapping]

            # Recompute fully_protected_ids after allocations
            fully_protected_ids = {
                fid for fid in fields_by_id
                if getattr(fields_by_id[fid], 'drones_for_full_protection', 0) > 0 and
                   current_prot.get(fid, 0) >= getattr(fields_by_id[fid], 'drones_for_full_protection', 0)
            }

        # 8) Step 4: Finalize
        for d in components:
            if d in mapping:
                continue
            if getattr(d, 'state', None) == 'protecting':
                tid = getattr(d, 'target_id', None)
                g = f"protecting {tid}" if tid is not None else None
                if g in group_ids:
                    mapping[d] = g
                    continue
            mapping[d] = "idle"

        # 9) Apply assignments (exactly once per drone)
        for d, g in mapping.items():
            environment.assign_group(d, g)