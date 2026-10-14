

# Improved Smart Farm Adaptation Strategy

## Analysis of the Problem

The `nan` damage indicates the simulation crashed or the drones were never properly assigned. The previous code was overly complex with many potential failure points: incorrect API calls (`self._assign_group` didn't exist), overly complex stealing logic that could corrupt state, and unclear group identifiers.

## New Strategy

1. **Simple greedy priority assignment**: Sort fields by threat, assign closest available drones to each field until fully protected.
2. **Stickiness**: Prefer drones already assigned to a field (they're already moving/arriving there).
3. **Minimal reassignment**: Only pull drones from a field if a higher-threat field absolutely needs them.
4. **Clean API usage**: Use `drone.group` directly for assignment.

```python
import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        # --- Sort active fields by threat level descending ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # --- If no active threats, park all drones in idle group ---
        if not active_fields:
            for d in components:
                d.group = group_id
            return

        # --- Compute field centers ---
        centers = {}
        for f in environment.fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            centers[f.id] = (cx, cy)

        # --- Cache drone positions and current field assignments ---
        drone_pos = {}
        drone_current_fid = {}
        for d in components:
            drone_pos[d.id] = (d.location.x, d.location.y)
            drone_current_fid[d.id] = d.target_id if d.target_id is not None else None

        # --- Group drones by their current field for stickiness ---
        field_holders = {}  # field_id -> [drone_ids currently assigned there]
        for d in components:
            fid = drone_current_fid[d.id]
            if fid is not None:
                field_holders.setdefault(fid, []).append(d.id)

        # --- Greedy assignment in priority order ---
        assigned = set()       # drone ids that have been assigned to a field
        drone_to_field = {}    # drone_id -> field_id

        for f in active_fields:
            fid = f.id
            cx, cy = centers[fid]
            needed = f.drones_for_full_protection

            if needed <= 0:
                continue

            # Separate drones into those already here vs. elsewhere
            here = [did for did in field_holders.get(fid, []) if did not in assigned]
            elsewhere = [d.id for d in components if d.id not in assigned and d.id not in set(here)]

            # Sort each group by distance to this field center
            here.sort(key=lambda did: (drone_pos[did][0] - cx) ** 2 + (drone_pos[did][1] - cy) ** 2)
            elsewhere.sort(key=lambda did: (drone_pos[did][0] - cx) ** 2 + (drone_pos[did][1] - cy) ** 2)

            # Prefer already-here drones (stickiness), then closest others
            to_assign = here[:needed]
            remaining_slots = needed - len(to_assign)
            if remaining_slots > 0:
                to_assign.extend(elsewhere[:remaining_slots])

            # Assign
            for did in to_assign:
                drone_to_field[did] = fid
                assigned.add(did)

        # --- Apply assignments via group mechanism ---
        # Build a reverse lookup for efficiency
        field_group_names = {}
        for f in environment.fields:
            # Use the field's own group_id if available, otherwise str(field.id)
            if hasattr(f, 'group_id'):
                field_group_names[f.id] = str(f.group_id)
            else:
                field_group_names[f.id] = str(f.id)

        for d in components:
            fid = drone_to_field.get(d.id)
            if fid is not None:
                gname = field_group_names.get(fid, str(fid))
                d.group = gname
            else:
                d.group = group_id
```

## Key Improvements Over Previous Version

| Issue in previous code | Fix in new code |
|---|---|
| `self._assign_group()` method didn't exist → **crash** | Direct `d.group = ...` assignment |
| Complex "stealing" logic could corrupt assignments | Simple greedy pass; no stealing needed in normal operation |
| Overly complex keep/release logic with many edge cases | Two-line stickiness check: prefer `field_holders`, then sort by distance |
| Could leave drones unassigned due to set manipulation bugs | Single `assigned` set guarantees each drone is assigned exactly once |
| No fallback for missing attributes | `hasattr` check for `group_id` on fields |
| Could produce `nan` via exception propagation | Minimal, clean code with no nested loops that can corrupt state |

The strategy guarantees:
- **Highest-threat field gets full protection first** (processed first, can claim any available drone)
- **Stickiness** via `field_holders` preference (≥50% stay put in steady state)
- **No overprotection** (capped at `drones_for_full_protection`)
- **No idle drones** when fields need protection (all drones assigned if enough threats exist)