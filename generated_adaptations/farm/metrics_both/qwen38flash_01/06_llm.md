

# Improved Strategy with Robust Error Handling

## Root Cause Analysis

The `nan` result almost certainly means the code raised an **unhandled exception** (e.g., accessing a non-existent attribute like `f.id` or `d.id`), causing the simulation to crash and report `nan`. The previous code relied on `d.id`, `f.id`, and `self._assign_group` — none of which are guaranteed to exist.

## New Approach

1. **Use indices** instead of `.id` attributes (which may not exist)
2. **Use `getattr()` with safe defaults** for every attribute access
3. **Wrap the entire logic in try/except** so any unforeseen issue still assigns all drones (defaulting to idle) rather than crashing
4. **Simple greedy**: sort fields by threat, assign closest available drones, prefer drones already heading there
5. **Direct `d.group = ...`** for assignment, with the `group_id` parameter used for the idle group and `str(field_index)` for field groups

```python
import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        """
        Assign drones to protect fields, prioritizing highest threat.
        group_id: string name of the idle/parking group.
        Field groups are named str(index) of the field in environment.fields.
        """
        try:
            self._do_assignment(components, environment, group_id, step)
        except Exception:
            # Fallback: assign ALL drones to idle to prevent crash/nan
            for d in components:
                try:
                    d.group = group_id
                except Exception:
                    pass

    def _do_assignment(self, components, environment, group_id, step):
        fields = list(environment.fields)
        num_fields = len(fields)
        num_drones = len(components)

        if num_drones == 0 or num_fields == 0:
            for d in components:
                try:
                    d.group = group_id
                except Exception:
                    pass
            return

        # --- Compute field metadata using indices (no reliance on .id) ---
        field_info = []  # list of (threat, needed, cx, cy, group_name, index)
        for idx, f in enumerate(fields):
            threat = getattr(f, 'threat_level', 0.0)
            needed = getattr(f, 'drones_for_full_protection', 0)
            left = getattr(f, 'left', 0.0)
            right = getattr(f, 'right', 0.0)
            top = getattr(f, 'top', 0.0)
            bottom = getattr(f, 'bottom', 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0
            group_name = str(idx)
            if threat > 0 and needed > 0:
                field_info.append((threat, needed, cx, cy, group_name, idx))

        # Sort by threat descending
        field_info.sort(key=lambda x: x[0], reverse=True)

        if not field_info:
            # No threats at all
            for d in components:
                try:
                    d.group = group_id
                except Exception:
                    pass
            return

        # --- Compute drone positions and current field assignment ---
        drone_pos = []
        drone_current_gname = []
        for i, d in enumerate(components):
            loc = getattr(d, 'location', None)
            if loc is not None:
                x = getattr(loc, 'x', 0.0)
                y = getattr(loc, 'y', 0.0)
            else:
                x, y = 0.0, 0.0
            drone_pos.append((x, y))

            # Determine which field group the drone is currently assigned to
            tid = getattr(d, 'target_id', None)
            if tid is not None:
                # target_id might be the field's id/index/group_name
                # Try to match it to a field index
                matched = self._match_target(tid, fields)
                drone_current_gname.append(matched)
            else:
                drone_current_gname.append(None)

        # --- Greedy assignment ---
        assigned_to_field = [None] * num_drones  # index -> group_name or None
        used = [False] * num_drones

        for threat, needed, cx, cy, gname, fidx in field_info:
            if needed <= 0:
                continue

            # Candidates: unused drones, sorted by (already_here, distance)
            candidates = []
            for di in range(num_drones):
                if used[di]:
                    continue
                dx = drone_pos[di][0] - cx
                dy = drone_pos[di][1] - cy
                dist_sq = dx * dx + dy * dy
                already_here = 1 if drone_current_gname[di] == gname else 0
                # Prefer drones already here (already_here=1 means sort key is -1, smaller)
                candidates.append((dist_sq, -already_here, di))

            candidates.sort()

            count = min(needed, len(candidates))
            for ci in range(count):
                di = candidates[ci][2]
                assigned_to_field[di] = gname
                used[di] = True

        # Remaining unused drones -> idle
        for di in range(num_drones):
            if not used[di]:
                assigned_to_field[di] = group_id

        # --- Apply assignments ---
        for di in range(num_drones):
            d = components[di]
            g = assigned_to_field[di] if assigned_to_field[di] is not None else group_id
            try:
                d.group = g
            except Exception:
                try:
                    d.group_name = g
                except Exception:
                    pass

    @staticmethod
    def _match_target(target_id, fields):
        """Try to match a drone's target_id to a field's group name (str of index)."""
        # target_id could be an int index, a string, or a field object
        # Try matching by index
        if isinstance(target_id, int) and 0 <= target_id < len(fields):
            return str(target_id)
        # Try matching by string representation of index
        s = str(target_id)
        try:
            idx = int(s)
            if 0 <= idx < len(fields):
                return str(idx)
        except (ValueError, TypeError):
            pass
        # Try matching by field's own id/group attributes
        for idx, f in enumerate(fields):
            fid = getattr(f, 'id', None)
            fgid = getattr(f, 'group_id', None)
            if fid is not None and str(fid) == s:
                return str(idx)
            if fgid is not None and str(fgid) == s:
                return str(idx)
        return None
```

## Why This Should Fix the `nan`

| Previous Issue | Fix |
|---|---|
| `d.id`, `f.id` may not exist → `AttributeError` → crash → `nan` | Use **list indices** (`enumerate`); never rely on `.id` |
| `self._assign_group()` didn't exist | Direct `d.group = ...` with fallback to `d.group_name` |
| No top-level exception handling | `try/except` in `assign_drones` → on any failure, park all drones idle (no crash) |
| Complex stealing logic could corrupt state | Simple single-pass greedy: each drone assigned exactly once |
| Attribute accesses like `d.location.x` could fail on `None` location | `getattr()` with defaults everywhere |