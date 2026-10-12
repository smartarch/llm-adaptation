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
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Current protectors per field
        current_protectors_by_field = {f.id: [] for f in fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_protectors_by_field:
                    current_protectors_by_field[tid].append(c)

        final_group = {}  # drone -> group_id

        # Threat map for quick access
        threat_map = {f.id: f.threat_level for f in fields}

        # Helper to distance-squared from a drone to a field center
        def dist2_to_field(drone, fid):
            cx, cy = centers[fid]
            loc = getattr(drone, "location", None)
            dx = (loc.x if loc is not None else 0) - cx
            dy = (loc.y if loc is not None else 0) - cy
            return dx * dx + dy * dy

        # Helper to gather candidate drones for a field
        def pick_candidates_for_field(fid, needed, avoid_ids=set()):
            candidates = []
            # 1) Idle or non-protecting drones
            for c in components:
                if c in final_group or c in avoid_ids:
                    continue
                if getattr(c, "state", None) != "protecting":
                    dist2 = dist2_to_field(c, fid)
                    candidates.append((dist2, c))

            # 2) Drones protecting fields with lower threat (prefer not to disrupt high-threat fields)
            for c in components:
                if c in final_group or c in avoid_ids:
                    continue
                if getattr(c, "state", None) == "protecting":
                    other = getattr(c, "target_id", None)
                    if other is not None and other in threat_map:
                        if threat_map[other] < threat_map(fid):
                            dist2 = dist2_to_field(c, fid)
                            candidates.append((dist2, c))

            # 3) As last resort, drones protecting equal or higher-threat fields
            if not candidates:
                for c in components:
                    if c in final_group or c in avoid_ids:
                        continue
                    if getattr(c, "state", None) == "protecting":
                        other = getattr(c, "target_id", None)
                        if other is not None:
                            dist2 = dist2_to_field(c, fid)
                            candidates.append((dist2, c))

            candidates.sort(key=lambda t: t[0])
            chosen = []
            for dist2, c in candidates:
                if len(chosen) >= needed:
                    break
                if c in final_group:
                    continue
                chosen.append(c)
            return chosen

        # Allocate per field in threat order
        for f in fields:
            fid = f.id
            curr = len(current_protectors_by_field.get(fid, []))
            need = max(0, f.drones_for_full_protection - curr)
            if need > 0:
                # First try with idle drones, then with lower-threat field protectors
                to_assign = pick_candidates_for_field(fid, need, avoid_ids=set(final_group.values()))
                for d in to_assign:
                    final_group[d] = f"protecting {fid}"

                # If still not enough, attempt a second pass to fill the remaining need
                if len(to_assign) < need:
                    remaining = need - len(to_assign)
                    extra = []
                    for c in components:
                        if c in final_group:
                            continue
                        if getattr(c, "state", None) != "protecting":
                            dist2 = dist2_to_field(c, fid)
                            extra.append((dist2, c))
                    extra.sort(key=lambda t: t[0])
                    for dist2, c in extra:
                        if len(to_assign) >= need:
                            break
                        if c in final_group:
                            continue
                        final_group[c] = f"protecting {fid}"
                        to_assign.append(c)

            # Ensure existing protectors stay in this field
            if curr > 0:
                for d in current_protectors_by_field.get(fid, []):
                    if d not in final_group:
                        final_group[d] = f"protecting {fid}"

        # Assign remaining drones
        for c in components:
            if c in final_group:
                continue
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid is not None:
                    final_group[c] = f"protecting {tid}"
                    continue
            final_group[c] = "idle"

        # Apply group assignments
        for c in components:
            environment.assign_group(c, final_group[c])