Reasoning and adaptation strategy (updated)

Goal: push the damage further down by more robustly distributing drones across multiple high-threat fields, while still guaranteeing exactly one assignment per drone.

What’s new:
- Multi-field budgeting: choose a small set of top-threat fields to fully protect (topK) based on current drone availability, and lock drones that are already protecting those fully protected fields.
- Two-phase allocation:
  - Phase 1 focuses on fully protecting the selected topK fields by moving the closest drones, but never stealing from a topK field unless the donor field has surplus (so we don’t break a full protection).
  - Phase 2 uses a deficit-driven, proximity-based approach to partially protect remaining fields. Donor constraints are respected so we don’t violate previously locked protections.
- All assignments are computed in a single final mapping and then applied in one pass (one environment.assign_group call per drone).

This approach aims to maximize fully protected high-threat fields first, then provide partial protection to others when possible, while ensuring correctness tests (one assignment per drone and valid group names).

Python code

```py
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
        centers = {}
        for fid in threat_ids:
            f = field_by_id[fid]
            centers[fid] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Max protection required per field
        max_protect = {fid: int(getattr(field_by_id[fid], "drones_for_full_protection", 0)) for fid in threat_ids}

        # Current protectors per field
        counts = {fid: 0 for fid in threat_ids}
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in threat_ids:
                counts[c.target_id] += 1

        total_drones = len(components)

        # Decide topK fields to fully protect given current budget
        threat_fields_sorted = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
        deficits = {fid: max(0, max_protect.get(fid, 0) - counts.get(fid, 0)) for fid in threat_ids}
        topK_set = set()
        budget = total_drones  # naive budget; will subtract deficits as we pick top fields

        for f in threat_fields_sorted:
            fid = f.id
            d = deficits.get(fid, 0)
            if d <= 0:
                topK_set.add(fid)
                continue
            if d <= budget:
                topK_set.add(fid)
                budget -= d
            else:
                # can't fully cover this field with remaining budget; skip for topK
                continue

        final_group_for = {}
        assigned = set()  # drone ids already assigned

        # Phase 0: lock drones currently protecting fully protected fields in topK_set
        for c in components:
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) in topK_set:
                fid = c.target_id
                if max_protect.get(fid, 0) > 0 and counts.get(fid, 0) >= max_protect[fid]:
                    final_group_for[c] = f"protecting {fid}"
                    assigned.add(id(c))

        # Phase 1: Fill deficits for topK fields (deficits > 0), using closest non-assigned drones
        deficits_topK = {fid: max(0, max_protect.get(fid, 0) - counts.get(fid, 0)) for fid in topK_set}
        for fid in sorted(list(topK_set), key=lambda x: counts.get(x, 0), reverse=True):
            needed = deficits_topK.get(fid, 0)
            if needed <= 0:
                continue
            center = centers[fid]

            candidates = []
            for c in components:
                if id(c) in assigned:
                    continue
                prev_fid = c.target_id if getattr(c, "state", "") == "protecting" else None
                # Donor constraint: avoid stealing from a topK field unless donor has surplus
                if prev_fid in topK_set and prev_fid is not None:
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
            for i in range(fill):
                drone = candidates[i][1]
                final_group_for[drone] = f"protecting {fid}"
                assigned.add(id(drone))
                counts[fid] = counts.get(fid, 0) + 1
                deficits_topK[fid] = max(0, max_protect.get(fid, 0) - counts[fid])

                prev_fid = candidates[i][2]
                if prev_fid is not None and prev_fid in threat_ids:
                    counts[prev_fid] = max(0, counts[prev_fid] - 1)

        # Phase 2: Allocate remaining drones to deficits across all fields (partial protection)
        deficits_all = {fid: max(0, max_protect.get(fid, 0) - counts.get(fid, 0)) for fid in threat_ids}
        while True:
            pending = [fid for fid in threat_ids if deficits_all.get(fid, 0) > 0]
            if not pending:
                break

            # Urgency: higher threat and larger deficit ratio
            def field_urg(fid):
                d = deficits_all.get(fid, 0)
                if d <= 0:
                    return -1.0
                maxp = max_protect.get(fid, 0)
                ratio = d / max(1, maxp)
                return field_by_id[fid].threat_level * (1.0 + ratio)

            target = max(pending, key=lambda fid: field_urg(fid))
            if field_urg(target) < 0:
                break

            center = centers[target]
            needed = deficits_all[target]

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
```