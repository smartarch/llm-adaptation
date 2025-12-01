from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat and a positive full-protection requirement
        threat_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0 and getattr(f, "drones_for_full_protection", 0) > 0
        ]

        # If no threat, put all drones idle
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Phase 0: Build current protectors by field (as observed now)
        protectors_by_field = {}
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    protectors_by_field.setdefault(tid, []).append(idx)

        # Phase 1: Decide which fields to fully protect using efficiency heuristic
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (getattr(f, "threat_level", 0) / max(1, getattr(f, "drones_for_full_protection", 1))),
            reverse=True
        )

        total_drones = len(components)
        remaining_capacity = total_drones
        selected_fields = []
        for f in threat_fields_sorted:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            if needed <= 0:
                continue
            if remaining_capacity >= needed:
                selected_fields.append(f)
                remaining_capacity -= needed

        # If nothing selected, default to the top threat field to avoid no-action
        if not selected_fields and threat_fields_sorted:
            selected_fields = [threat_fields_sorted[0]]

        # Phase 1: Allocate for selected fields, reusing current protectors where possible
        assigned = {}        # drone_index -> group_id
        allocated = set()      # drones already assigned to some protecting group

        # Process selected fields in order of threat (highest first)
        for f in sorted(selected_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            center = center_of(f)
            center_x, center_y = center
            needed = int(getattr(f, "drones_for_full_protection", 0))
            if needed <= 0:
                continue

            current = protectors_by_field.get(f.id, [])
            # Filter out those already allocated
            current = [idx for idx in current if idx not in allocated]

            # Sort current protectors by distance to center
            def dist_to_center_idx(idx):
                d = components[idx]
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center_x
                dy = loc.y - center_y
                return (dx * dx + dy * dy) ** 0.5

            current_sorted = sorted(current, key=lambda i: dist_to_center_idx(i))
            keep_list = current_sorted[:min(len(current_sorted), needed)]
            for idx in keep_list:
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)

            remaining = max(0, needed - len(keep_list))
            if remaining > 0:
                # Use closest unallocated drones (not currently protecting anyone) to fill
                candidates = []
                for idx, d in enumerate(components):
                    if idx in allocated:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = loc.x - center_x
                        dy = loc.y - center_y
                        dist = (dx * dx + dy * dy) ** 0.5
                    candidates.append((dist, idx))
                candidates.sort()
                for i in range(min(remaining, len(candidates))):
                    idx = candidates[i][1]
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)

        # Phase 2: Partial protection with remaining drones
        # Compute remaining_to_protect for each field after Phase 1
        remaining_to_protect = {}
        def field_cent(fid):
            for ff in threat_fields:
                if ff.id == fid:
                    return center_of(ff)
            return (0.0, 0.0)

        for f in threat_fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            current_count = sum(1 for idx, gid in assigned.items() if gid == f"protecting {f.id}")
            remaining_to_protect[f.id] = max(0, required - current_count)

        # Build list of available drones for partial allocation
        # Do not move drones that are currently protecting somewhere else (to avoid breaking existing protections)
        available = [idx for idx, d in enumerate(components) if idx not in allocated and getattr(d, "state", "") != "protecting"]

        # Fields that still need protection (by threat)
        fields_needing = [f for f in threat_fields if remaining_to_protect.get(f.id, 0) > 0]
        # Allocate remaining drones to the needs, prioritizing higher threat
        # For each available drone, assign to the best field it can help (most threat, closest center)
        # Simple greedy per-field allocation: iterate fields by threat, assign nearest available drones until filled
        for f in sorted(fields_needing, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            center = center_of(f)
            need = remaining_to_protect.get(f.id, 0)
            if need <= 0:
                continue
            # Recompute distances to this field for available drones
            dist_list = []
            for idx in available:
                d = components[idx]
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = loc.x - center[0]
                    dy = loc.y - center[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                dist_list.append((dist, idx))
            dist_list.sort()
            taken = 0
            for dist, idx in dist_list:
                if taken >= need:
                    break
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)
                available.remove(idx)
                taken += 1
            # update remaining_to_protect
            remaining_to_protect[f.id] = max(0, remaining_to_protect.get(f.id, 0) - taken)

        # Final: assign groups
        for idx, d in enumerate(components):
            if idx in assigned:
                environment.assign_group(d, assigned[idx])
            else:
                environment.assign_group(d, "idle")