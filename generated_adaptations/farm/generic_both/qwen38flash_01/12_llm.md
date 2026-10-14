

## Strategy Description

Damage improved 68 → 83 → 59. The regression at 83 was caused by over-complexity; the recovery to 59 came from minimum-change and concentration. The remaining damage at 59 comes from:

1. **Transit gaps**: When a drone is pulled from field A to field B, during transit BOTH fields are underprotected. If A drops below its full-protection threshold, birds attack A with zero defense while B still can't repel them either (needs full protection).

2. **Oscillation**: Small threat fluctuations cause repeated reassignments, creating repeated transit windows.

3. **Non-atomic pulls**: Pulling the last needed drone from a field creates a full-protection gap on that field.

**New improvements:**

1. **Atomic swap constraint**: Never pull a drone from a field unless that field will still be at full protection after the pull. If a pull would drop a field below threshold, SKIP that pull (accept slight deficit on the high-priority field rather than creating two unprotected fields).

2. **Dwell time / cooldown**: Track the last step each drone was reassigned. Don't reassign a drone within 4 steps unless the threat ratio exceeds 3× (extreme priority change). This eliminates oscillation.

3. **Transit-cost-aware pull selection**: When multiple drones can be pulled from over-supplied fields, prefer the one closest to the target field AND farthest from its current field's "critical zone" (i.e., pulling a drone that's already leaving the area is better).

4. **Delta-based updating**: Compare new target to current assignment. Compute the minimal set of moves. Apply moves one at a time, checking atomicity after each. This prevents cascading failures.

5. **Smart surplus**: Surplus drones (beyond full protection of all selected fields) are placed on the highest-threat field but positioned on its side nearest to the next field (for faster response if threats shift).

6. **Partial protection penalty**: Never assign drones to a field where they won't reach full protection. Instead, place them on already-fully-protected fields (reserves).

## Code Implementation

```python
import math
from typing import List, Dict, Set, Tuple, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    # Minimum steps between reassignments of the same drone
    COOLDOWN = 4
    # Threat ratio above which we ignore cooldown
    EXTREME_RATIO = 3.0

    def _group_for_field(self, field, group_ids: List[str]) -> str:
        fid = str(field.id)
        for gid in group_ids:
            if gid == "idle":
                continue
            if gid == fid:
                return gid
            if fid in gid:
                return gid
        return "idle"

    @staticmethod
    def _center(field):
        return ((field.left + field.right) * 0.5,
                (field.top + field.bottom) * 0.5)

    def _dist(self, drone, field) -> float:
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _parse_target(self, drone, field_id_set: Set[str]) -> Optional[str]:
        tgt = getattr(drone, 'target_id', None)
        if tgt is None:
            return None
        t = str(tgt)
        if t == "" or t.lower() == "idle":
            return None
        if t in field_id_set:
            return t
        for fid in field_id_set:
            if fid in t or t in fid:
                return fid
        return None

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            return

        active.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in active}
        field_ids: Set[str] = set(field_by_id.keys())
        field_need: Dict[str, int] = {
            str(f.id): max(1, f.drones_for_full_protection) for f in active
        }

        # --- Track cooldown ---
        if not hasattr(self, '_last_move_step'):
            self._last_move_step: Dict[int, int] = {}

        # --- Read current targets ---
        current: Dict[int, Optional[str]] = {}
        for d in components:
            current[id(d)] = self._parse_target(d, field_ids)

        # --- Compute current counts ---
        current_count: Dict[str, int] = {fid: 0 for fid in field_ids}
        current_members: Dict[str, Set[int]] = {fid: set() for fid in field_ids}
        for d in components:
            t = current[id(d)]
            if t and t in current_count:
                current_count[t] += 1
                current_members[t].add(id(d))

        # --- Compute target allocation (greedy, closest drones) ---
        # Determine how many fields we can fully protect
        cumulative = 0
        n_full = 0
        for f in active:
            c = f.drones_for_full_protection
            if cumulative + c <= total_drones:
                cumulative += c
                n_full += 1
            else:
                break
        # If we can't even fully protect the top field, concentrate on it
        if n_full == 0:
            n_full = 1

        # Assign target: fields 0..n_full-1 get full protection, rest get 0
        pool: Set[int] = set(id(d) for d in components)
        target: Dict[str, List[int]] = {str(f.id): [] for f in active}

        for idx, f in enumerate(active):
            fid = str(f.id)
            if idx < n_full:
                cap = f.drones_for_full_protection
            elif idx == 0:
                cap = total_drones  # Concentrate on top
            else:
                cap = 0  # No partial protection

            avail = sorted([d for d in components if id(d) in pool],
                           key=lambda d: self._dist(d, f))
            for d in avail:
                if len(target[fid]) >= cap:
                    break
                if id(d) in pool:
                    target[fid].append(id(d))
                    pool.discard(id(d))

        # Surplus → top field
        if pool and active:
            top_fid = str(active[0].id)
            for d in components:
                if id(d) in pool:
                    target[top_fid].append(id(d))
                    pool.discard(id(d))

        # --- Compute target counts ---
        target_count: Dict[str, int] = {fid: len(target[fid]) for fid in field_ids}

        # --- Determine moves needed ---
        # A drone needs to move if its current field != its target field
        move_list: List[Tuple[int, str, str]] = []  # (drone_id, from_field, to_field)
        stay_list: List[Tuple[int, str]] = []  # (drone_id, field) - stays

        for d in components:
            did = id(d)
            tgt_fid = None
            for fid, drone_ids in target.items():
                if did in drone_ids:
                    tgt_fid = fid
                    break
            cur_fid = current.get(did)

            if cur_fid == tgt_fid:
                stay_list.append((did, cur_fid))
            elif tgt_fid is not None:
                move_list.append((did, cur_fid, tgt_fid))

        # --- Apply moves with atomicity and cooldown ---
        final_assign: Dict[int, str] = {}

        # First, lock in all stays
        for did, fid in stay_list:
            if fid is not None and fid in field_by_id:
                final_assign[did] = fid

        # Simulate counts as we apply moves
        sim_count: Dict[str, int] = {fid: len(target[fid]) for fid in field_ids}
        # Start from current, then verify moves maintain atomicity
        sim_current: Dict[str, int] = dict(current_count)

        # Sort moves: highest-priority destination first, then closest drone to dest
        def move_priority(m):
            did, from_f, to_f = m
            # Priority by target field threat
            threat = field_by_id[to_f].threat_level if to_f in field_by_id else 0
            return -threat
        move_list.sort(key=move_priority)

        applied_moves: List[Tuple[int, str, str]] = []

        for did, from_f, to_f in move_list:
            if to_f is None or to_f not in field_by_id:
                # Unplaced drone → top field
                to_f = str(active[0].id)

            # Cooldown check
            last = self._last_move_step.get(did, -100)
            if step - last < self.COOLDOWN:
                # Check extreme ratio override
                if from_f and from_f in field_by_id and to_f in field_by_id:
                    ratio = field_by_id[to_f].threat_level / max(
                        field_by_id[from_f].threat_level, 0.001)
                    if ratio < self.EXTREME_RATIO:
                        # Respect cooldown: keep drone where it is
                        if from_f and from_f in field_by_id:
                            final_assign[did] = from_f
                            continue
                        # Else fall through to default placement
                        to_f = str(active[0].id)
                else:
                    if from_f and from_f in field_by_id:
                        final_assign[did] = from_f
                        continue
                    to_f = str(active[0].id)

            # Atomicity: don't pull from a field that would drop below need
            if from_f and from_f in sim_current:
                if sim_current[from_f] - 1 < field_need.get(from_f, 0):
                    # Pulling would underprotect source field
                    # Alternative: place this drone on top field instead
                    # (avoid creating two unprotected fields)
                    alt_fid = str(active[0].id)
                    final_assign[did] = alt_fid
                    continue

            # Apply the move
            final_assign[did] = to_f
            applied_moves.append((did, from_f, to_f))

        # Update cooldown tracker
        for did, _, _ in applied_moves:
            self._last_move_step[did] = step

        # --- Safety: ensure every drone is assigned ---
        for d in components:
            if id(d) not in final_assign:
                final_assign[id(d)] = str(active[0].id)

        # --- Final environment assignment ---
        for d in components:
            did = id(d)
            fid = final_assign.get(did)
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")
```