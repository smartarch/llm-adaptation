

# Root Cause Identified: Default Values Causing Field Skipping

## The Bug

In all my previous attempts, when I read `f.drones_for_full_protection` and the attribute was missing or returned a non-standard value, my helper function returned a **default of `0`**. This meant **every field was skipped** during assignment (since `if need <= 0: continue`). All drones went idle. The simulation then computed damage with **zero protected drones**, yielding `nan` (division by zero).

## The Fix

- Use **sensible defaults** (`1` for `drones_for_full_protection`, `0.1` for threat when attribute exists but is unparseable).
- **Only skip a field** if `threat_level` is explicitly a real number ≤ 0.
- Keep assignment logic to **only `d.group`** — no other attribute writes that could corrupt drone state.
- Use **`f.group_id`** as the group identifier (matching the API naming convention where the idle parameter is also called `group_id`).
- **Return the assignment list** as well, in case the framework reads it from the return value.

```python
class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        # 1. Collect fields that need protection
        field_needs = []
        for f in environment.fields:
            threat = getattr(f, 'threat_level', None)
            need   = getattr(f, 'drones_for_full_protection', None)

            # Only skip if threat is EXPLICITLY a non-positive number
            if threat is not None:
                try:
                    threat = float(threat)
                except (TypeError, ValueError):
                    threat = 0.1  # assume threat exists but is odd
            else:
                threat = 0.1  # attribute missing: assume there IS a threat

            if threat <= 0:
                continue

            # Default to 2 drones if attribute is missing or bad
            if need is not None:
                try:
                    need = int(need)
                except (TypeError, ValueError):
                    need = 2
            else:
                need = 2
            if need < 1:
                need = 1

            # Group name: use field's own group_id, fall back to its id
            gname = getattr(f, 'group_id', None)
            if gname is None:
                gname = getattr(f, 'id', None)
            if gname is None:
                continue  # can't identify this field's group
            gname = str(gname)

            cx = (getattr(f, 'left', 0) + getattr(f, 'right', 0)) / 2.0
            cy = (getattr(f, 'top',  0) + getattr(f, 'bottom', 0)) / 2.0

            field_needs.append((threat, need, gname, cx, cy))

        # 2. Sort: highest threat first
        field_needs.sort(key=lambda t: t[0], reverse=True)

        # 3. Assign drones: closest first, no over-assignment
        n = len(components)
        drone_groups = [group_id] * n   # default: idle
        used = [False] * n

        for threat, need, gname, cx, cy in field_needs:
            # pick 'need' closest unused drones
            cands = []
            for i in range(n):
                if used[i]:
                    continue
                d = components[i]
                loc = d.location
                dx = loc.x - cx
                dy = loc.y - cy
                cands.append((dx * dx + dy * dy, i))
            cands.sort()

            for j in range(min(need, len(cands))):
                di = cands[j][1]
                drone_groups[di] = gname
                used[di] = True

        # 4. Apply assignments
        for i, d in enumerate(components):
            d.group = drone_groups[i]

        # 5. Also return the assignment (in case framework uses it)
        return drone_groups
```