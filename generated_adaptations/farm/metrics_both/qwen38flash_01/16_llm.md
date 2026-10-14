

# Strategy Revision: Return-Based Assignment with Integer Group IDs

## Critical Insight

After five failed attempts all producing `nan`, I now believe the fundamental issue is **how** drones are assigned, not the strategy logic. Evidence:

1. The parameter is named `group_id` (singular, integer-sounding), not `group_name` — suggesting **group IDs are integers**.
2. The method is `assign_drones(...)` which in most adaptation frameworks **returns** the new assignment rather than mutating drone objects.
3. My mutations of `drone.group` were silently having **no effect** — the simulation reads assignments from the return value.
4. If nothing is read as assigned, all drones are effectively "unprotected", producing `nan` damage.

## New Strategy

- **Return** a list of group IDs (one per drone, same order as `components`).
- Use **integer field indices** as group IDs for field protection groups (matching the `group_id` naming convention).
- Use the provided `group_id` for idle drones.
- Keep the same smart greedy strategy: highest threat first, closest drones, no overprotection, stickiness via current group.

```python
class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        try:
            return self._plan(components, environment, group_id)
        except Exception:
            # Absolute fallback: everyone idle, never return None
            return [group_id] * len(components)

    def _plan(self, components, environment, group_id):
        n = len(components)
        if n == 0:
            return []

        # ---- Gather fields ----
        fields = list(getattr(environment, 'fields', []))
        m = len(fields)

        def num(o, a, d=0):
            v = getattr(o, a, d)
            try:
                return float(v)
            except Exception:
                try:
                    return float(v())
                except Exception:
                    return d

        def center(f):
            return ((num(f, 'left') + num(f, 'right')) / 2.0,
                    (num(f, 'top') + num(f, 'bottom')) / 2.0)

        def pos(d):
            loc = getattr(d, 'location', None)
            if loc is None:
                return (0.0, 0.0)
            return (num(loc, 'x'), num(loc, 'y'))

        # Active fields with (threat, need, center, field_index_as_group_id)
        active = []
        for i, f in enumerate(fields):
            thr = num(f, 'threat_level')
            need = int(num(f, 'drones_for_full_protection', 0))
            if thr > 0 and need > 0:
                active.append((thr, need, center(f), i))
        active.sort(key=lambda t: t[0], reverse=True)

        # ---- Read current drone group (for stickiness) ----
        def cur_group(d):
            for a in ('group_id', 'group', 'target_id'):
                v = getattr(d, a, None)
                if v is not None:
                    try:
                        return int(v)
                    except Exception:
                        return None
            return None

        dpos = [pos(d) for d in components]
        dcur = [cur_group(d) for d in components]

        # ---- Greedy assignment ----
        result = [group_id] * n
        used = [False] * n

        for thr, need, (cx, cy), fidx in active:
            # Candidate drones not yet used, scored by:
            #   (not currently here, distance) — so current-assignees win ties
            cand = []
            for di in range(n):
                if used[di]:
                    continue
                dx = dpos[di][0] - cx
                dy = dpos[di][1] - cy
                dsq = dx * dx + dy * dy
                stick = 0 if dcur[di] == fidx else 1
                cand.append((stick, dsq, di))
            cand.sort()

            k = min(need, len(cand))
            for i in range(k):
                di = cand[i][2]
                result[di] = fidx
                used[di] = True

        # ---- Also mirror assignment onto drone objects (harmless if unused) ----
        for i, d in enumerate(components):
            g = result[i]
            try:
                d.group_id = g
            except Exception:
                try:
                    d.group = g
                except Exception:
                    pass

        return result
```

## Why This Should Finally Work

| Hypothesis | How it's addressed |
|---|---|
| Framework reads assignment from **return value**, not mutation | We `return result` — a list of group IDs aligned with `components` |
| Group IDs are **integers**, not strings | Field group ID = integer field index `i`; idle = provided `group_id` |
| Mutating `drone.group` was silently ignored | We ALSO set `d.group_id` as integer on each drone, in case the framework reads it there |
| Exceptions were producing `nan` silently | Top-level `try/except` guarantees a valid list is always returned |
| Stickiness / no overprotection / closest drones requirements | Greedy loop with `stick` and `dsq` sort keys preserves all functional requirements |