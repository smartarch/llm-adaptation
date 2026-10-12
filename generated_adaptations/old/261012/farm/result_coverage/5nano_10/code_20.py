from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_num(self, obj, attr, default=0.0):
        v = getattr(obj, attr, default)
        try:
            return float(v)
        except Exception:
            return float(default)

    def _field_center(self, f):
        left = self._get_num(f, "left", 0.0)
        right = self._get_num(f, "right", 0.0)
        top = self._get_num(f, "top", 0.0)
        bottom = self._get_num(f, "bottom", 0.0)
        return (left + right) / 2.0, (top + bottom) / 2.0

    def _drone_dist2_to(self, d, cx, cy):
        loc = getattr(d, "location", None)
        if loc is None:
            dx = -cx
            dy = -cy
        else:
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
        return dx*dx + dy*dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        threatened = [
            f for f in environment.fields
            if self._get_num(f, "threat_level", 0.0) > 0.0
        ]

        # 2) If no threatened fields, idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 3) Sort fields by threat (desc) and id (asc) for determinism
        threatened.sort(
            key=lambda f: (
                -self._get_num(f, "threat_level", 0.0),
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
            centers[fid] = self._field_center(f)

            cap = int(getattr(f, "drones_for_full_protection", 0))
            if cap < 0:
                cap = 0
            current = len(current_by_field.get(fid, []))
            counts[fid] = current
            needs[fid] = max(0, cap - current)

        total_need = sum(needs.values())

        # If nothing needs protection, idle all non-assigned drones
        if total_need == 0:
            for d in components:
                if d not in assigned:
                    environment.assign_group(d, "idle")
            return

        # 6) Prepare pool of available drones (not already assigned)
        available = [d for d in components if d not in assigned]

        # 7) Phase 1: Proportional distribution across fields
        total_threat = sum(self._get_num(f, "threat_level", 0.0) for f in threatened)
        if total_threat <= 0:
            total_threat = 1.0  # guard

        # Compute per-field proportional extras (bounded by cap - current)
        extras_target = {}
        total_drones = len(components)
        used_existing = 0
        for f in threatened:
            fid = getattr(f, "id", None)
            cap = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            current = len(current_by_field.get(fid, []))
            needs_f = max(0, cap - current)
            # proportional share based on threat
            th = self._get_num(f, "threat_level", 0.0)
            if total_threat > 0:
                frac = th / total_threat
            else:
                frac = 0.0
            approx_add = int(round(frac * total_drones))
            add = max(0, min(cap - current, approx_add))
            extras_target[fid] = add
            used_existing += current

        available_after_existing = max(0, total_drones - used_existing)

        total_extras = sum(extras_target.values())
        if total_extras > available_after_existing:
            # Greedily reduce extras from fields with largest extras
            # Build list of (fid, extra)
            items = [(fid, extras_target[fid]) for f in threatened for fid in [getattr(f, "id", None)]]
            # Normalize to unique per field
            items = []
            for f in threatened:
                fid = getattr(f, "id", None)
                items.append((fid, extras_target.get(fid, 0)))
            while total_extras > available_after_existing:
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
        for f in threatened:
            fid = getattr(f, "id", None)
            need = extras_target.get(fid, 0)
            if need <= 0:
                continue
            cx, cy = centers.get(fid, (0.0, 0.0))
            if not available:
                break

            # Sort available by distance to field center
            available.sort(key=lambda d: self._drone_dist2_to(d, cx, cy))

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
                    th = self._get_num(f, "threat_level", 0.0)
                    score = th * need
                    if score > best_score or (abs(score - best_score) < 1e-9 and (best_fid is None or str(fid) < str(best_fid))):
                        best_score = score
                        best_fid = fid
                        best_need = need

            if best_fid is None:
                break

            cx, cy = centers.get(best_fid, (0.0, 0.0))

            best_drone = None
            best_dist = None
            for d in available:
                d2 = self._drone_dist2_to(d, cx, cy)
                if best_drone is None or d2 < best_dist:
                    best_drone = d
                    best_dist = d2

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