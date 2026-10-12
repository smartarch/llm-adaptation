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

        # Precompute centers and threat map
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}
        threat_map = {f.id: f.threat_level for f in fields}

        # Current protectors per field
        current_protectors_by_field = {fid: [] for fid in field_by_id}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_protectors_by_field:
                    current_protectors_by_field[tid].append(c)

        final_group = {}  # drone -> group_id

        def dist2_to_field(drone, fid):
            cx, cy = centers[fid]
            loc = getattr(drone, "location", None)
            dx = (loc.x if loc is not None else 0) - cx
            dy = (loc.y if loc is not None else 0) - cy
            return dx*dx + dy*dy

        # Pre-assign existing protectors to their fields
        for fid, drones in current_protectors_by_field.items():
            for d in drones:
                final_group[d] = f"protecting {fid}"

        # Prepare a prioritized list of fields to attempt full protection
        field_candidates = []
        for f in fields:
            fid = f.id
            curr = len(current_protectors_by_field.get(fid, []))
            need = max(0, f.drones_for_full_protection - curr)
            if need > 0:
                score = f.threat_level / max(1, need)
                field_candidates.append((score, fid))
        field_candidates.sort(key=lambda t: (-t[0], t[1]))

        # Allocate drones to each field in order of the computed score
        for _, fid in field_candidates:
            f = field_by_id[fid]
            curr = len(current_protectors_by_field.get(fid, []))
            need = max(0, f.drones_for_full_protection - curr)
            if need <= 0:
                continue

            chosen = 0

            # 1) Idle or non-protecting drones (closest first)
            idle_candidates = [c for c in components if c not in final_group and getattr(c, "state", None) != "protecting"]
            idle_candidates.sort(key=lambda c: dist2_to_field(c, fid))
            for c in idle_candidates:
                if chosen >= need:
                    break
                final_group[c] = f"protecting {fid}"
                chosen += 1

            if chosen >= need:
                continue

            # 2) Drones protecting lower-threat fields
            lower_candidates = []
            for c in components:
                if c in final_group:
                    continue
                if getattr(c, "state", None) == "protecting":
                    other = getattr(c, "target_id", None)
                    if other in threat_map and threat_map[other] < threat_map[fid]:
                        lower_candidates.append(c)
            lower_candidates.sort(key=lambda c: dist2_to_field(c, fid))
            for c in lower_candidates:
                if chosen >= need:
                    break
                final_group[c] = f"protecting {fid}"
                chosen += 1

            if chosen >= need:
                continue

            # 3) Drones protecting equal or higher-threat fields (last resort)
            equal_or_higher = []
            for c in components:
                if c in final_group:
                    continue
                if getattr(c, "state", None) == "protecting":
                    other = getattr(c, "target_id", None)
                    if other in threat_map:
                        equal_or_higher.append(c)
            equal_or_higher.sort(key=lambda c: dist2_to_field(c, fid))
            for c in equal_or_higher:
                if chosen >= need:
                    break
                final_group[c] = f"protecting {fid}"
                chosen += 1

        # Remaining drones: preserve existing protections if possible, else idle
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