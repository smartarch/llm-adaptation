from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level desc, then by id for determinism
        fields.sort(key=lambda f: (-f.threat_level, f.id))

        field_by_id = {f.id: f for f in fields}

        # Precompute centers for distance calculations
        centers = {}
        for f in fields:
            centers[f.id] = (
                (f.left + f.right) / 2.0,
                (f.top + f.bottom) / 2.0,
            )

        # Current protectors per field
        current_protectors_by_field = {f.id: [] for f in fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_protectors_by_field:
                    current_protectors_by_field[tid].append(c)

        final_group = {}  # drone -> group_id

        # For each field in priority order, attempt to reach full protection
        for f in fields:
            fid = f.id
            curr = len(current_protectors_by_field.get(fid, []))
            needed = max(0, f.drones_for_full_protection - curr)
            if needed == 0:
                # Ensure existing protectors stay in their group
                for d in current_protectors_by_field.get(fid, []):
                    final_group[d] = f"protecting {fid}"
                continue

            cx, cy = centers[fid]

            # Build candidate pools (not yet assigned in this iteration)
            candidates = []

            # 1) Idle or non-protecting drones
            for c in components:
                if c in final_group:
                    continue
                if getattr(c, "state", None) != "protecting":
                    loc = getattr(c, "location", None)
                    dx = (loc.x if loc is not None else 0) - cx
                    dy = (loc.y if loc is not None else 0) - cy
                    dist2 = dx * dx + dy * dy
                    candidates.append((dist2, c))

            # 2) Drones protecting other fields (potential reallocations)
            for c in components:
                if c in final_group:
                    continue
                if getattr(c, "state", None) == "protecting":
                    other = getattr(c, "target_id", None)
                    if other is not None and other in field_by_id and other != fid:
                        loc = getattr(c, "location", None)
                        dx = (loc.x if loc is not None else 0) - cx
                        dy = (loc.y if loc is not None else 0) - cy
                        dist2 = dx * dx + dy * dy
                        candidates.append((dist2, c))

            # Sort by distance and take closest drones
            candidates.sort(key=lambda t: t[0])

            chosen = 0
            for dist2, c in candidates:
                if chosen >= needed:
                    break
                if c in final_group:
                    continue
                final_group[c] = f"protecting {fid}"
                chosen += 1

            # Ensure existing protectors are accounted for
            for d in current_protectors_by_field.get(fid, []):
                if d not in final_group:
                    final_group[d] = f"protecting {fid}"

        # Assign remaining drones: preserve current protection where possible, otherwise idle
        for c in components:
            if c in final_group:
                continue
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid is not None and tid in field_by_id:
                    final_group[c] = f"protecting {tid}"
                    continue
            final_group[c] = "idle"

        # Apply group assignments
        for c in components:
            environment.assign_group(c, final_group[c])