from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat fields: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Map field_id -> field for quick access
        field_by_id = {f.id: f for f in threat_fields}
        threat_ids = set(field_by_id.keys())

        # Sort fields by threat level descending
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers
        centers = {
            fid: ((field_by_id[fid].left + field_by_id[fid].right) / 2.0,
                  (field_by_id[fid].top + field_by_id[fid].bottom) / 2.0)
            for fid in threat_ids
        }

        # Current counts per field
        counts = {fid: 0 for fid in threat_ids}
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in threat_ids:
                counts[c.target_id] += 1

        # Determine fully protected fields (to lock them)
        max_protect_map = {fid: int(getattr(field_by_id[fid], "drones_for_full_protection", 0)) for fid in threat_ids}
        fully_protected_fields = {fid for fid in threat_ids if max_protect_map[fid] > 0 and counts[fid] >= max_protect_map[fid]}

        final_group_for = {}
        assigned = set()  # drone ids that have been assigned
        locked = set()    # drones locked to a fully protected field (kept in place)

        # Phase 0: Lock drones currently protecting fully protected fields
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in fully_protected_fields:
                fid = c.target_id
                final_group_for[c] = f"protecting {fid}"
                assigned.add(id(c))
                locked.add(id(c))

        # Phase 1: Fill deficits to fully protect top fields without moving locked drones
        deficits = {}
        for fid in fully_protected_fields:
            deficits[fid] = max(0, max_protect_map[fid] - counts[fid])

        # We will fill deficits for fully protected fields using only non-locked drones.
        # To avoid breaking other fully protected fields, also avoid moving drones that are protecting
        # fields in fully_protected_fields.
        for fid in sorted(list(fully_protected_fields), key=lambda x: counts[x], reverse=True):
            needed = deficits.get(fid, 0)
            if needed <= 0:
                continue

            center = centers[fid]
            available = []
            for c in components:
                if id(c) in assigned or id(c) in locked:
                    continue
                # Do not steal from a field that's currently fully protected (prev_fid in fully_protected_fields)
                prev_fid = c.target_id if getattr(c, "state", "") == "protecting" else None
                if prev_fid in fully_protected_fields:
                    continue
                loc = getattr(c, "location", None)
                dist = float("inf")
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = ((loc.x - center[0]) ** 2 + (loc.y - center[1]) ** 2) ** 0.5
                available.append((dist, c))
            available.sort(key=lambda t: t[0])

            fill = min(needed, len(available))
            for i in range(fill):
                drone = available[i][1]
                # If drone was protecting some field, moving away impacts that field's count
                prev_fid = drone.target_id if getattr(drone, "state", "") == "protecting" else None
                final_group_for[drone] = f"protecting {fid}"
                assigned.add(id(drone))
                counts[fid] = counts.get(fid, 0) + 1
                deficits[fid] = max(0, deficits.get(fid, 0) - 1)

                if prev_fid is not None and prev_fid in threat_ids:
                    # If we moved away from a non-fully-protected field, adjust its count/deficit
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)
                    # Recompute deficit for that field
                    deficits[prev_fid] = max(0, max_protect_map[prev_fid] - counts[prev_fid])

        # Phase 2: Allocate remaining drones to partially protect other fields (not necessarily fully protected yet)
        # Recompute deficits for all fields
        deficits_all = {}
        for fid in threat_ids:
            deficits_all[fid] = max(0, max_protect_map[fid] - counts[fid])

        # Helper: urgency for a field (non-negative means needs protection)
        def field_urgency(fid):
            max_protect = max_protect_map[fid]
            deficit = deficits_all.get(fid, 0)
            if deficit <= 0:
                return -1.0
            deficit_ratio = deficit / max(1, max_protect)
            # Tie-break by threat level
            return field_by_id[fid].threat_level * (1.0 + deficit_ratio)

        while True:
            pending = [fid for fid in threat_ids if deficits_all.get(fid, 0) > 0]
            if not pending:
                break

            # Pick field with highest urgency
            target_fid = max(pending, key=lambda fid: field_urgency(fid))
            if field_urgency(target_fid) < 0:
                break

            center = centers[target_fid]
            needed = deficits_all[target_fid]

            # Candidates: drones not yet assigned, do not break fully protected fields when possible
            candidates = []
            for c in components:
                if id(c) in assigned:
                    continue
                loc = getattr(c, "location", None)
                dist = float("inf")
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = ((loc.x - center[0]) ** 2 + (loc.y - center[1]) ** 2) ** 0.5
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            fill = min(needed, len(candidates))
            if fill <= 0:
                break

            for i in range(fill):
                drone = candidates[i][1]
                # If drone was protecting some field, moving away may affect that field
                prev_fid = drone.target_id if getattr(drone, "state", "") == "protecting" else None
                # Ensure we don't reassign to a field that would violate constraints across priority (optional guard)
                final_group_for[drone] = f"protecting {target_fid}"
                assigned.add(id(drone))
                counts[target_fid] = counts.get(target_fid, 0) + 1
                deficits_all[target_fid] = max(0, deficits_all[target_fid] - 1)

                if prev_fid is not None and prev_fid in threat_ids:
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)
                    deficits_all[prev_fid] = max(0, max_protect_map[prev_fid] - counts[prev_fid])

        # Phase 3: Any drones not assigned yet become idle
        for c in components:
            if id(c) not in assigned:
                final_group_for[c] = "idle"

        # Phase 4: Apply assignments (exactly once per drone)
        for c in components:
            environment.assign_group(c, final_group_for[c])