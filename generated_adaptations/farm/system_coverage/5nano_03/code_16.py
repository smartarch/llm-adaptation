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

        # Total number of drones
        total_drones = len(components)

        # Sort threat fields by threat level descending for topK selection
        threat_fields_sorted = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers
        centers = {
            fid: ((field_by_id[fid].left + field_by_id[fid].right) / 2.0,
                  (field_by_id[fid].top + field_by_id[fid].bottom) / 2.0)
            for fid in threat_ids
        }

        # Max protection per field
        max_protect = {fid: int(getattr(field_by_id[fid], "drones_for_full_protection", 0)) for fid in threat_ids}

        # Current protectors per field
        counts = {fid: 0 for fid in threat_ids}
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in threat_ids:
                counts[c.target_id] += 1

        # Determine topK fields to fully protect given the drone budget
        topK_set = set()
        budget = total_drones
        for f in threat_fields_sorted:
            fid = f.id
            req = max_protect.get(fid, 0)
            if req <= 0:
                continue
            # If we include this field, we need 'req' drones (beyond current protectors)
            deficit_here = max(0, req - counts[fid])
            if deficit_here <= 0:
                # Already fully protected
                topK_set.add(fid)
                continue
            if deficit_here <= budget - 0:  # naive budget check; we only ensure we don't exceed total drones
                topK_set.add(fid)
                budget -= deficit_here
            else:
                # Can't fully cover this field with remaining budget
                break

        # Phase preparation: lock fully protected fields
        final_group_for = {}
        assigned = set()  # drone ids assigned
        # Lock drones currently protecting fully protected fields (topK) that are already full
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in topK_set:
                fid = c.target_id
                if max_protect.get(fid, 0) > 0 and counts.get(fid, 0) >= max_protect[fid]:
                    final_group_for[c] = f"protecting {fid}"
                    assigned.add(id(c))

        # Phase 0: If any topK field is already fully protected by a current protector, ensure those drones stay
        # This is implicitly handled by the lock above.

        # Phase 1: Fill deficits for topK fields (deficits >= 0)
        deficits = {fid: max(0, max_protect.get(fid, 0) - counts.get(fid, 0)) for fid in topK_set}
        # Ensure we fill using non-locked drones and avoid stealing from non-surplus topK fields
        for fid in sorted(list(topK_set), key=lambda x: counts.get(x, 0), reverse=True):
            needed = deficits.get(fid, 0)
            if needed <= 0:
                continue
            center = centers[fid]
            candidates = []
            for c in components:
                if id(c) in assigned:
                    continue
                # Donor constraint: avoid stealing from a topK field unless that donor field has surplus
                prev_fid = c.target_id if getattr(c, "state", "") == "protecting" else None
                if prev_fid in topK_set:
                    donor_surplus = counts.get(prev_fid, 0) - max_protect.get(prev_fid, 0)
                    if donor_surplus <= 0:
                        continue  # cannot steal from this topK field
                loc = getattr(c, "location", None)
                dist = float("inf")
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = ((loc.x - center[0]) ** 2 + (loc.y - center[1]) ** 2) ** 0.5
                candidates.append((dist, c, prev_fid))
            candidates.sort(key=lambda t: t[0])

            fill = min(needed, len(candidates))
            for i in range(fill):
                drone = candidates[i][1]
                final_group_for[drone] = f"protecting {fid}"
                assigned.add(id(drone))
                counts[fid] = counts.get(fid, 0) + 1
                deficits[fid] = max(0, max_protect.get(fid, 0) - counts[fid])

                prev_fid = candidates[i][2]
                if prev_fid is not None and prev_fid in threat_ids:
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)

        # Phase 2: Allocate remaining drones to deficits across all fields (partially protect)
        deficits_all = {fid: max(0, max_protect.get(fid, 0) - counts.get(fid, 0)) for fid in threat_ids}
        while True:
            pending = [fid for fid in threat_ids if deficits_all.get(fid, 0) > 0]
            if not pending:
                break

            # Urgency: prioritize higher threat and larger deficit ratio
            def field_urgency(fid):
                d = deficits_all.get(fid, 0)
                if d <= 0:
                    return -1.0
                maxp = max_protect.get(fid, 0)
                ratio = d / max(1, maxp)
                return field_by_id[fid].threat_level * (1.0 + ratio)

            target = max(pending, key=lambda fid: field_urgency(fid))
            if field_urgency(target) < 0:
                break

            center = centers[target]
            needed = deficits_all[target]

            # Build candidates (not assigned yet)
            candidates = []
            for c in components:
                if id(c) in assigned:
                    continue
                prev_fid = c.target_id if getattr(c, "state", "") == "protecting" else None
                # Donor constraint: avoid breaking topK unless donor has surplus
                if prev_fid in topK_set:
                    donor_surplus = counts.get(prev_fid, 0) - max_protect.get(prev_fid, 0)
                    if donor_surplus <= 0:
                        continue
                loc = getattr(c, "location", None)
                dist = float("inf")
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = ((loc.x - center[0]) ** 2 + (loc.y - center[1]) ** 2) ** 0.5
                candidates.append((dist, c, prev_fid))
            candidates.sort(key=lambda t: t[0])

            fill = min(needed, len(candidates))
            if fill <= 0:
                break

            for i in range(fill):
                drone = candidates[i][1]
                final_group_for[drone] = f"protecting {target}"
                assigned.add(id(drone))
                counts[target] = counts.get(target, 0) + 1
                deficits_all[target] = max(0, max_protect.get(target, 0) - counts[target])

                prev_fid = candidates[i][2]
                if prev_fid is not None and prev_fid in threat_ids:
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)
                    deficits_all[prev_fid] = max(0, max_protect.get(prev_fid, 0) - counts[prev_fid])

        # Phase 3: Any unassigned drones become idle
        for c in components:
            if id(c) not in assigned:
                final_group_for[c] = "idle"

        # Phase 4: Apply assignments (exactly once per drone)
        for c in components:
            environment.assign_group(c, final_group_for.get(c, "idle"))