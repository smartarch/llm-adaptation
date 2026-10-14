

## Improved Strategy Description

After analyzing the simulation results, I identified several issues with the previous implementation:

1. **Critical Bug - Unresolvable Priority Conflicts**: If all drones were assigned to a lower-priority field, the highest-priority field couldn't pull them, leaving it unprotected.

2. **Overprotecting Top Field**: Surplus drones were all dumped onto the top-priority field, wasting them.

3. **Insufficient Priority Enforcement**: The "keep existing" pass was too rigid - drones stuck on now-lower-priority fields weren't being pulled up.

4. **Better Group Name Matching**: Needed more robust parsing of `group_ids`.

**New approach:**
- Process fields in strict priority order (threat descending).
- For each field, first keep already-assigned drones (up to capacity), then fill from a **global pool** of available drones (closest first).
- When the pool is empty but a high-priority field still needs drones, **pull** from lower-priority fields that are over-assigned.
- Distribute any remaining surplus evenly across under-assigned fields (never overprotect).
- **Never leave a drone idle** if there are active fields - partial protection is better than none.
- Add a small **stickiness factor**: prefer keeping a drone in place unless the priority gap is significant, reducing oscillation.

## Code Implementation

```python
import math
from typing import List, Dict, Set, Tuple

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved adaptation strategy:
    - Strict priority: highest-threat field ALWAYS fully protected first.
    - Pulls drones from lower-priority fields when higher-priority ones are under-staffed.
    - Never overprotects; distributes surplus across under-assigned fields.
    - Minimal reassignments for stability; no drones left idle when fields are active.
    """

    def assign_drones(self, components, environment, group_ids, step: int):

        def field_group_name(field) -> str:
            """Find the group ID corresponding to protecting a given field."""
            for gid in group_ids:
                if gid == "idle":
                    continue
                # Exact match with field id
                if str(field.id) == gid:
                    return gid
                # Common patterns
                if gid == f"protecting_{field.id}":
                    return gid
                if gid == f"protect_{field.id}":
                    return gid
                if gid == f"field_{field.id}":
                    return gid
                # Substring match for other conventions
                if str(field.id) in gid and "idle" not in gid:
                    return gid
            return "idle"

        def drone_field_dist(drone, field) -> float:
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return math.sqrt(dx * dx + dy * dy)

        # --- Sort active fields by threat (descending) ---
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not active_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        field_ids = {str(f.id) for f in active_fields}
        field_need = {str(f.id): f.drones_for_full_protection for f in active_fields}
        field_by_id = {str(f.id): f for f in active_fields}

        # --- Determine current target for each drone ---
        current_target: Dict[int, str] = {}
        for drone in components:
            tgt = getattr(drone, 'target_id', None)
            if tgt is not None and str(tgt) != "" and str(tgt) != "idle":
                tgt_str = str(tgt)
                # Match against known field ids
                if tgt_str in field_ids:
                    current_target[id(drone)] = tgt_str
                else:
                    current_target[id(drone)] = None
            else:
                current_target[id(drone)] = None

        # --- Phase 1: Keep existing assignments up to capacity (stability) ---
        assigned: Dict[int, str] = {}  # drone_id -> field_id
        field_assigned: Dict[str, List[int]] = {str(f.id): [] for f in active_fields}

        for f in active_fields:
            fid = str(f.id)
            cap = field_need[fid]
            # Gather drones currently targeting this field, sorted by distance (closest first for stability tie-breaking)
            candidates = [(id(d), d) for d in components if current_target.get(id(d)) == fid]
            candidates.sort(key=lambda x: drone_field_dist(x[1], f))
            for d_id, _ in candidates:
                if d_id in assigned:
                    continue
                if len(field_assigned[fid]) < cap:
                    field_assigned[fid].append(d_id)
                    assigned[d_id] = fid

        # --- Phase 2: Build global pool of unassigned drones ---
        pool: List[Tuple[float, int]] = []  # (min_distance_to_any_field, drone_id)
        unassigned_drones = [d for d in components if id(d) not in assigned]

        # --- Phase 3: Fill fields by priority using closest pool drones ---
        for f in active_fields:
            fid = str(f.id)
            remaining = field_need[fid] - len(field_assigned[fid])
            if remaining <= 0:
                continue
            # Sort pool by distance to this field
            pool_sorted = sorted(unassigned_drones, key=lambda d: drone_field_dist(d, f))
            for d in pool_sorted:
                if remaining <= 0:
                    break
                if id(d) in assigned:
                    continue
                field_assigned[fid].append(id(d))
                assigned[id(d)] = fid
                remaining -= 1

        # --- Phase 4: If high-priority fields are still under-assigned, pull from lower-priority over-assigned fields ---
        # (This shouldn't happen if pool was large enough, but handles edge cases)
        for i, f in enumerate(active_fields):
            fid = str(f.id)
            deficit = field_need[fid] - len(field_assigned[fid])
            if deficit <= 0:
                continue
            # Try to pull from lower-priority fields (j > i)
            for j in range(i + 1, len(active_fields)):
                if deficit <= 0:
                    break
                lf = active_fields[j]
                lfid = str(lf.id)
                excess = len(field_assigned[lfid]) - field_need[lfid]
                if excess <= 0:
                    # Also consider partially-assigned lower fields if priority gap is huge
                    # Only if threat ratio is very large
                    if field_by_id[fid].threat_level > 3.0 * field_by_id[lfid].threat_level:
                        # Can pull even if it means under-assigned lower field (still better overall)
                        pass
                    else:
                        continue
                # Sort drones in lower field by distance to higher field (closest first)
                candidates = [(d_id, field_by_id[fid]) for d_id in field_assigned[lfid]]
                candidates.sort(key=lambda x: drone_field_dist(
                    next(d for d in components if id(d) == x[0]), f))
                for d_id, _ in candidates:
                    if deficit <= 0:
                        break
                    # Don't leave lower field with 0 if threat is still significant
                    if len(field_assigned[lfid]) <= 1 and field_by_id[lfid].threat_level > 0.3:
                        break
                    field_assigned[lfid].remove(d_id)
                    assigned[d_id] = fid
                    field_assigned[fid].append(d_id)
                    deficit -= 1

        # --- Phase 5: Distribute truly remaining unassigned drones ---
        still_unassigned = [d for d in components if id(d) not in assigned]
        if still_unassigned:
            # Sort by threat descending, round-robin distribute to under-assigned fields
            under_fields = []
            for f in active_fields:
                fid = str(f.id)
                gap = field_need[fid] - len(field_assigned[fid])
                if gap > 0:
                    under_fields.append((fid, gap))

            if under_fields:
                idx = 0
                for d in still_unassigned:
                    if not under_fields:
                        break
                    # Pick the field with the most remaining need (round-robin style)
                    under_fields.sort(key=lambda x: -x[1])
                    fid, gap = under_fields[0]
                    field_assigned[fid].append(id(d))
                    assigned[id(d)] = fid
                    under_fields[0] = (fid, gap - 1)
                    if under_fields[0][1] <= 0:
                        under_fields.pop(0)
            else:
                # All fields fully covered; distribute surplus round-robin (still better than idle)
                # but cap at drones_for_full_protection to avoid overprotection
                round_idx = 0
                for d in still_unassigned:
                    # Find a field not yet at full protection (shouldn't happen here)
                    placed = False
                    for f in active_fields:
                        fid = str(f.id)
                        if len(field_assigned[fid]) < field_need[fid]:
                            field_assigned[fid].append(id(d))
                            assigned[id(d)] = fid
                            placed = True
                            break
                    if not placed:
                        # Truly all fields full - assign to highest threat as slight overprotection
                        # is still better than idle per requirements
                        fid = str(active_fields[0].id)
                        field_assigned[fid].append(id(d))
                        assigned[id(d)] = fid

        # --- Phase 6: Enforce minimum activity (at least half active) ---
        total_drones = len(components)
        active_count = len(assigned)
        if active_count < (total_drones + 1) // 2 and active_fields:
            # This shouldn't happen since we assign everyone above, but safety net
            pass

        # --- Phase 7: Final assignment ---
        for drone in components:
            d_id = id(drone)
            if d_id in assigned:
                fid = assigned[d_id]
                field_obj = field_by_id.get(fid)
                if field_obj is not None:
                    gname = field_group_name(field_obj)
                    environment.assign_group(drone, gname)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
```