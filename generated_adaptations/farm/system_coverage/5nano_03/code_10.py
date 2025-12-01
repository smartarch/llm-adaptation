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

        # Precompute field centers
        centers = {
            fid: ((field_by_id[fid].left + field_by_id[fid].right) / 2.0,
                  (field_by_id[fid].top + field_by_id[fid].bottom) / 2.0)
            for fid in threat_ids
        }

        # Count current protectors per field
        counts = {fid: 0 for fid in threat_ids}
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in threat_ids:
                counts[c.target_id] += 1

        # Final mapping: component -> group_id
        final_group_for = {}
        assigned = set()  # ids of drones already assigned

        # Step 0: If any field is already fully protected, keep those drones there
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in threat_ids:
                fid = c.target_id
                max_protect = int(getattr(field_by_id[fid], "drones_for_full_protection", 0))
                if counts[fid] >= max_protect:
                    final_group_for[c] = f"protecting {fid}"
                    assigned.add(id(c))

        # Step 1: Compute deficits for each field
        deficits = {}
        for fid in threat_ids:
            max_protect = int(getattr(field_by_id[fid], "drones_for_full_protection", 0))
            deficits[fid] = max(0, max_protect - counts[fid])

        # Helper: field urgency (higher means we should allocate there first)
        def field_urgency(fid):
            max_protect = int(getattr(field_by_id[fid], "drones_for_full_protection", 0))
            deficit = deficits.get(fid, 0)
            if deficit <= 0:
                return -1.0
            deficit_ratio = deficit / max(1, max_protect)
            return field_by_id[fid].threat_level * (1.0 + deficit_ratio)

        # Step 2: Greedily allocate closest available drones to fields with deficit
        while True:
            # Fields with remaining deficit
            pending = [fid for fid in threat_ids if deficits.get(fid, 0) > 0]
            if not pending:
                break

            # Choose the field with highest urgency
            target_fid = max(pending, key=lambda fid: field_urgency(fid))
            if field_urgency(target_fid) < 0:
                break

            center = centers[target_fid]
            needed = deficits[target_fid]

            # Build available drones (not yet assigned)
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
                # If drone was protecting some field, and that field still has deficit > 0, moving might be ok
                prev_fid = None
                if getattr(drone, "state", "") == "protecting" and getattr(drone, "target_id", None) in threat_ids:
                    prev_fid = drone.target_id

                # Reallocate: assign to target field
                final_group_for[drone] = f"protecting {target_fid}"
                assigned.add(id(drone))

                # Update deficits and counts to reflect relocation
                counts[target_fid] = counts.get(target_fid, 0) + 1
                deficits[target_fid] = max(0, deficits[target_fid] - 1)

                if prev_fid is not None and prev_fid in threat_ids:
                    # We moved drone away from prev_fid; decrease its count
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)
                    deficits[prev_fid] = deficits.get(prev_fid, 0) + 1

        # Step 3: Any drones not assigned yet become idle
        for c in components:
            if id(c) not in assigned:
                final_group_for[c] = "idle"

        # Step 4: Apply assignments (exactly once per drone)
        for c in components:
            environment.assign_group(c, final_group_for[c])