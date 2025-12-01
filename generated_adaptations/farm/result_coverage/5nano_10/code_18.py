from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        threatened = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]

        # 2) If no threatened fields, idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 3) Sort fields by threat (desc) and id (asc) for determinism
        threatened.sort(
            key=lambda f: (
                -float(getattr(f, "threat_level", 0.0)),
                str(getattr(f, "id", ""))
            )
        )

        # 4) Re-assign currently protecting drones to their groups (explicit)
        current_by_field = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                if fid is not None:
                    current_by_field.setdefault(fid, []).append(d)

        assigned = set()
        for fid, ds in current_by_field.items():
            for dd in ds:
                environment.assign_group(dd, f"protecting {fid}")
                assigned.add(dd)

        # 5) Compute centers and initial counts per field
        centers = {}
        needs = {}       # drones still needed to reach full protection per field
        counts = {}      # current protectors per field (within this tick)

        for f in threatened:
            fid = getattr(f, "id", None)
            cx = (getattr(f, "left", 0.0) + getattr(f, "right", 0.0)) / 2.0
            cy = (getattr(f, "top", 0.0) + getattr(f, "bottom", 0.0)) / 2.0
            centers[fid] = (cx, cy)

            req = int(getattr(f, "drones_for_full_protection", 0))
            if req < 0:
                req = 0
            current = len(current_by_field.get(fid, []))
            counts[fid] = current
            needs[fid] = max(0, req - current)

        total_need = sum(needs.values())

        # If nothing needs protection, idle all non-assigned drones
        if total_need == 0:
            for d in components:
                if d not in assigned:
                    environment.assign_group(d, "idle")
            return

        # 6) Prepare pool of available drones (not already assigned)
        available = [d for d in components if d not in assigned]

        # Helper to get center by field id
        def center_of(fid):
            return centers.get(fid, (0.0, 0.0))

        # 7) Phase 1: Proportional distribution across fields (bounded by per-field caps)
        total_threat = sum(getattr(f, "threat_level", 0.0) for f in threatened)
        if total_threat <= 0:
            total_threat = 1.0  # guard, though should not occur because threatened exists

        # Compute per-field fractional target extras (bounded by cap)
        existing_total = sum(len(current_by_field.get(getattr(f, "id", None), [])) for f in threatened)
        total_drones = len(components)
        extras_target = {}
        for f in threatened:
            fid = getattr(f, "id", None)
            current = len(current_by_field.get(fid, []))
            cap = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            # fraction of total drones allocated to this field (approx)
            frac = getattr(f, "threat_level", 0.0) / total_threat
            approx_add = int(round(frac * total_drones))
            add = max(0, min(cap - current, approx_add))
            if add < 0:
                add = 0
            extras_target[fid] = add

        # Normalize extras so total adds do not exceed available drones
        used_existing = sum(len(current_by_field.get(getattr(f, "id", None), [])) for f in threatened)
        available_after_existing = max(0, total_drones - used_existing)
        total_extras = sum(extras_target.values())
        if total_extras > available_after_existing:
            # Greedy reduction: reduce from fields with largest extras first
            # Build a list of (fid, extra) and repeatedly decrement the largest
            items = sorted(
                ((fid, extras_target[fid]) for f in threatened for fid in [getattr(f, "id", None)]),
                key=lambda x: -x[1]
            )
            # Correction: build proper list cleanly
            items = []
            for f in threatened:
                fid = getattr(f, "id", None)
                items.append((fid, extras_target.get(fid, 0)))
            # Reduce until within limit
            while total_extras > available_after_existing:
                # find the field with the largest remaining extra
                max_fid = None
                max_extra = -1
                for fid, ex in items:
                    if ex > max_extra:
                        max_extra = ex
                        max_fid = fid
                if max_extra <= 0 or max_fid is None:
                    break
                extras_target[max_fid] -= 1
                total_extras -= 1

        # Apply Phase 1 extras: allocate to fields by closest drones
        # Build a mutable list of available drones
        for f in threatened:
            fid = getattr(f, "id", None)
            need = extras_target.get(fid, 0)
            if need <= 0:
                continue
            cx, cy = center_of(fid)
            if not available:
                break

            # Sort by distance to field center
            def dist2_to_field(dr):
                loc = getattr(dr, "location", None)
                dx = (getattr(loc, "x", 0.0) - cx)
                dy = (getattr(loc, "y", 0.0) - cy)
                return dx*dx + dy*dy

            available.sort(key=dist2_to_field)

            while need > 0 and available:
                d = available.pop(0)
                environment.assign_group(d, f"protecting {fid}")
                assigned.add(d)
                need -= 1
                counts[fid] = counts.get(fid, 0) + 1

        # 8) Phase 2: If drones remain, allocate incrementally to fields needing protection
        while available:
            best_fid = None
            best_score = -1.0
            best_need = 0

            for f in threatened:
                fid = getattr(f, "id", None)
                need = needs.get(fid, 0)
                if need > 0:
                    th = float(getattr(f, "threat_level", 0.0))
                    score = th * need
                    if score > best_score or (abs(score - best_score) < 1e-9 and (best_fid is None or str(fid) < str(best_fid))):
                        best_score = score
                        best_fid = fid
                        best_need = need

            if best_fid is None:
                break  # no field needs additional protection

            cx, cy = center_of(best_fid)

            # Pick the closest available drone
            best_drone = None
            best_dist = None
            for d in available:
                loc = getattr(d, "location", None)
                dx = (getattr(loc, "x", 0.0) - cx)
                dy = (getattr(loc, "y", 0.0) - cy)
                dist2 = dx*dx + dy*dy
                if best_drone is None or dist2 < best_dist:
                    best_drone = d
                    best_dist = dist2

            if best_drone is None:
                break

            environment.assign_group(best_drone, f"protecting {best_fid}")
            assigned.add(best_drone)
            available.remove(best_drone)

            needs[best_fid] = needs.get(best_fid, 0) - 1
            counts[best_fid] = counts.get(best_fid, 0) + 1

        # 9) Any drones not assigned stay idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")