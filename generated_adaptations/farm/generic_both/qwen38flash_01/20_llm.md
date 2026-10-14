

## Strategy Analysis

The trajectory (51.3 → 112.0) shows the exposure/adjacency/variance tracking was **actively harmful**. The root cause: exposure tracking creates oscillation — when a high-threat field pulls drones away from field B, B becomes "exposed," gets boosted, and pulls drones back. This ping-pong wastes every step in transit.

**The winning principle from all runs: simple, fast, greedy reaction with minimal moves.**

The one targeted improvement that should actually help: **field-selection hysteresis** (not drone-level hysteresis). If field X was in last step's protected set, keep it there unless a replacement field is clearly better (>25% threat gap). This prevents two similarly-threatened fields from repeatedly stealing drones from each other, while still reacting instantly to genuine threat changes.

## Code Implementation

```python
import math
from typing import List, Dict, Set, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    # Hysteresis: keep previously-protected field unless new candidate is this much better
    FIELD_HYSTERESIS = 0.25
    # Move cap fraction (top field exempt)
    MAX_MOVES_FRACTION = 0.40

    def _group_for_field(self, field, group_ids: List[str]) -> str:
        fid = str(field.id)
        for gid in group_ids:
            if gid == "idle":
                continue
            if gid == fid:
                return gid
        for gid in group_ids:
            if gid == "idle":
                continue
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

    def _field_dist(self, f1, f2) -> float:
        c1 = self._center(f1)
        c2 = self._center(f2)
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

    def _parse_target(self, drone, field_id_set: Set[str]) -> Optional[str]:
        tgt = getattr(drone, 'target_id', None)
        if tgt is None:
            return None
        t = str(tgt)
        if not t or t.lower() == "idle":
            return None
        if t in field_id_set:
            return t
        for fid in field_id_set:
            if fid in t or t in fid:
                return fid
        return None

    def _compute_protected_set(self, active_sorted, total_drones, prev_protected_ids):
        """
        Determine which fields to fully protect this step.
        Greedy by threat, but with hysteresis: a field in prev_protected_ids
        stays unless a non-protected field has significantly higher threat.
        """
        # Greedy selection (no hysteresis)
        greedy_ids = []
        cumulative = 0
        for f in active_sorted:
            c = f.drones_for_full_protection
            if cumulative + c <= total_drones:
                cumulative += c
                greedy_ids.append(str(f.id))
            else:
                break
        if not greedy_ids:
            greedy_ids = [str(active_sorted[0].id)] if active_sorted else []

        # Hysteresis: for fields in prev_protected that aren't in greedy,
        # check if they should stay
        if prev_protected_ids:
            field_by_id = {str(f.id): f for f in active_sorted}
            for pid in prev_protected_ids:
                if pid in greedy_ids:
                    continue
                if pid not in field_by_id:
                    continue  # field no longer active
                prev_f = field_by_id[pid]
                # Find the lowest-threat field currently in greedy set
                # that could be replaced
                if not greedy_ids:
                    greedy_ids.append(pid)
                    continue
                worst_in_greedy = max(greedy_ids, key=lambda fid: field_by_id[fid].threat_level
                                      if fid in field_by_id else 999)
                worst_f = field_by_id[worst_in_greedy]
                # Replace only if new field is significantly better
                if prev_f.threat_level > worst_f.threat_level * (1 + self.FIELD_HYSTERESIS):
                    # Actually prev is better than worst — but we picked greedy already
                    # This means greedy is correct; prev field is worse. Skip.
                    pass
                # Alternative: if prev field was in greedy last step but not this step,
                # check if the field that replaced it is much better
                # Find which non-prev field is in greedy but wasn't in prev
                new_entries = [g for g in greedy_ids if g not in prev_protected_ids]
                for ne in new_entries:
                    if ne not in field_by_id:
                        continue
                    new_f = field_by_id[ne]
                    if prev_f.threat_level > new_f.threat_level * (1 - self.FIELD_HYSTERESIS):
                        # prev is competitive — swap them
                        greedy_ids.remove(ne)
                        greedy_ids.append(pid)
                        # Re-sort greedy by threat
                        greedy_ids.sort(key=lambda fid: field_by_id[fid].threat_level
                                        if fid in field_by_id else 0, reverse=True)
                        break

        return greedy_ids

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            self._prev_protected = []
            return

        # Sort by raw threat descending
        active.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in environment.fields}
        field_ids: Set[str] = {str(f.id) for f in environment.fields}

        # --- Previous protected set (for hysteresis) ---
        prev_protected = getattr(self, '_prev_protected', [])

        # --- Determine protected fields ---
        protected_ids = self._compute_protected_set(active, total_drones, prev_protected)
        self._prev_protected = list(protected_ids)

        protected_fields = [field_by_id[fid] for fid in protected_ids if fid in field_by_id]
        # Ensure protected_fields is sorted by threat for assignment priority
        protected_fields.sort(key=lambda f: f.threat_level, reverse=True)
        protected_ids_sorted = [str(f.id) for f in protected_fields]

        # --- Current drone targets (in-transit = at target) ---
        current: Dict[int, Optional[str]] = {}
        for d in components:
            current[id(d)] = self._parse_target(d, field_ids)

        # --- Build target allocation: closest drones to each protected field ---
        pool: Set[int] = set(id(d) for d in components)
        target: Dict[str, List[int]] = {str(f.id): [] for f in active}

        for f in protected_fields:
            fid = str(f.id)
            cap = f.drones_for_full_protection
            avail = sorted([d for d in components if id(d) in pool],
                           key=lambda d: self._dist(d, f))
            for d in avail:
                if len(target[fid]) >= cap:
                    break
                if id(d) in pool:
                    target[fid].append(id(d))
                    pool.discard(id(d))

        # Surplus: pre-position on protected field nearest to the next threat
        if pool:
            next_field = None
            for f in active:
                if str(f.id) not in protected_ids_sorted:
                    next_field = f
                    break
            for d in [d for d in components if id(d) in pool]:
                if next_field and protected_fields:
                    best_f = min(protected_fields,
                                 key=lambda pf: self._field_dist(pf, next_field))
                else:
                    best_f = protected_fields[0] if protected_fields else active[0]
                target[str(best_f.id)].append(id(d))
                pool.discard(id(d))

        if pool:
            top = protected_ids_sorted[0] if protected_ids_sorted else str(active[0].id)
            for d in components:
                if id(d) in pool:
                    target[top].append(id(d))
                    pool.discard(id(d))

        # --- Assign with minimum change ---
        final: Dict[int, str] = {}
        claimed: Set[int] = set()

        # Phase 1: drones already on target field stay put
        for fid in protected_ids_sorted:
            for did in target[fid]:
                if current.get(did) == fid:
                    final[did] = fid
                    claimed.add(did)

        # Phase 2: needed moves, sorted by target threat priority
        needed_moves: List[Tuple[int, str]] = []
        for fid in protected_ids_sorted:
            for did in target[fid]:
                if did not in claimed:
                    needed_moves.append((did, fid))

        # Sort: higher threat target first, then closest drone
        def move_key(m):
            did, fid = m
            threat = field_by_id[fid].threat_level if fid in field_by_id else 0
            dist = self._dist(next(d for d in components if id(d) == did),
                              field_by_id[fid])
            return (-threat, dist)
        needed_moves.sort(key=move_key)

        # Tiered cap: top field unlimited, others capped
        max_non_top = max(1, int(total_drones * self.MAX_MOVES_FRACTION))
        applied_non_top = 0
        top_fid = protected_ids_sorted[0] if protected_ids_sorted else None

        for did, fid in needed_moves:
            if fid == top_fid:
                final[did] = fid
                claimed.add(did)
            elif applied_non_top < max_non_top:
                final[did] = fid
                claimed.add(did)
                applied_non_top += 1
            else:
                # Can't move — stay put
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = fid
                claimed.add(did)

        # Safety: any unassigned drone
        for d in components:
            did = id(d)
            if did not in final:
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = protected_ids_sorted[0] if protected_ids_sorted else str(active[0].id)

        # --- Push to environment ---
        for d in components:
            fid = final.get(id(d))
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")
```