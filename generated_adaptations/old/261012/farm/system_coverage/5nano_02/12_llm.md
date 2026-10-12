Reasoning and improved adaptation strategy

New approach rationale
- Objective: reduce total damage by more intelligently allocating drones, while still guaranteeing one group per drone.
- Core idea: prioritize filling deficits using the closest idle drones first. Only when idle drones are unavailable do we cautiously reallocate from other fields that currently have spare protection (i.e., current_protect > drones_for_full_protection).
- Benefits:
  - Keeps currently protected fields intact unless there is guaranteed spare capacity to move a drone without breaking protection.
  - Reduces travel distance by primarily using idle drones located near high-threat fields.
  - Maintains a simple, interpretable plan: each field with threat gets its deficit filled with the nearest eligible drones, in threat-descending order.
- This approach tends to reduce damage more when there are multiple threatened fields and enough idle drones nearby, while still respecting protection guarantees.

Implementation notes
- Process fields in order of threat_level (highest first).
- For each field, try to fill deficit with:
  - Idle drones first (closest to the field center).
  - If needed, drones currently protecting other fields that have spare protection (current_protect[from_field] > drones_for_full_protection[from_field]).
- After planning, assign every drone to exactly one group (idle or protecting a specific field) in a single pass.

Code

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        plan = {}  # drone -> target_group (exactly one assignment per drone)

        if not fields:
            # No threat: idle all drones
            for d in components:
                plan[d] = "idle"
        else:
            # Precompute field centers and required counts
            centers = {
                f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)
                for f in fields
            }
            required_map = {f.id: int(getattr(f, 'drones_for_full_protection', 0)) for f in fields}

            # Current protection counts per field
            current_protect = {f.id: 0 for f in fields}
            for d in components:
                if getattr(d, 'state', None) == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid in current_protect:
                        current_protect[tid] += 1

            # Sort fields by threat level (highest first)
            fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

            assigned = set()  # drones already assigned in this plan

            for f in fields_sorted:
                fid = f.id
                deficit = max(0, required_map.get(fid, 0) - current_protect.get(fid, 0))
                if deficit <= 0:
                    continue

                cx, cy = centers[fid]

                # Phase 1: use idle drones (prefer not moving existing protections)
                idle_candidates = []
                for d in components:
                    if d in plan:
                        continue
                    if getattr(d, 'state', None) == 'protecting':
                        # Skip drones currently protecting any field
                        continue
                    loc = getattr(d, 'location', None)
                    dist = float('inf')
                    if loc is not None:
                        dx = getattr(loc, 'x', 0.0) - cx
                        dy = getattr(loc, 'y', 0.0) - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    idle_candidates.append((dist, d))
                idle_candidates.sort(key=lambda t: t[0])
                take = min(deficit, len(idle_candidates))
                for i in range(take):
                    drone = idle_candidates[i][1]
                    plan[drone] = f"protecting {fid}"
                    current_protect[fid] += 1
                    deficit -= 1
                    assigned.add(drone)

                # If still deficit, Phase 2: reallocate from fields with spare protection
                if deficit > 0:
                    donor_candidates = []
                    for d in components:
                        if d in plan:
                            continue
                        if getattr(d, 'state', None) == 'protecting':
                            from_field = getattr(d, 'target_id', None)
                            # Can donate only if that field has spare protection
                            if current_protect.get(from_field, 0) > required_map.get(from_field, 0):
                                loc = getattr(d, 'location', None)
                                dist = float('inf')
                                if loc is not None:
                                    dx = getattr(loc, 'x', 0.0) - cx
                                    dy = getattr(loc, 'y', 0.0) - cy
                                    dist = (dx*dx + dy*dy) ** 0.5
                                donor_candidates.append((dist, d, from_field))
                    donor_candidates.sort(key=lambda t: t[0])
                    for dist, drone, from_field in donor_candidates:
                        if deficit <= 0:
                            break
                        plan[drone] = f"protecting {fid}"
                        current_protect[fid] = current_protect.get(fid, 0) + 1
                        if from_field is not None:
                            current_protect[from_field] = max(0, current_protect.get(from_field, 0) - 1)
                        deficit = max(0, required_map.get(fid, 0) - current_protect.get(fid, 0))
                        assigned.add(drone)

            # All remaining drones become idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments (exactly one per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)
```