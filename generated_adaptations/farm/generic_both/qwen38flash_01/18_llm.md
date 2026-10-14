

## Strategy Description

Trajectory analysis (148→68→83→59→68→57.7→**51.3**) shows momentum+pre-positioning+move-capping helps. Remaining damage is dominated by:

1. **Exposure duration**: A field unprotected for 5 steps takes ~5× more damage than one unprotected for 1. Current algorithm doesn't penalize chronic exposure.
2. **Move cap too tight**: 33% cap means if the top field suddenly needs 5 more drones, it takes 2-3 steps to get them — each step is full damage.
3. **No spatial contagion model**: Birds fleeing field A attack the nearest field B next. We ignore adjacency.
4. **No threat variance awareness**: A field oscillating between 0.2 and 0.9 is more urgent (could spike) than one steady at 0.5.

**New improvements:**

1. **Exposure-weighted priority**: Track consecutive steps each field has been unprotected. Effective threat = threat × (1 + 0.25 × min(exposed_steps, 5)). Chronically exposed fields get pulled up the priority list, getting drones before damage compounds.

2. **Top-field exemption from move cap**: The #1 threat field can pull unlimited drones this step. Only moves for fields ranked #2+ are capped. This ensures the most urgent field responds instantly.

3. **Spatial adjacency boost**: Fields physically close to a currently-protected high-threat field get +10% priority (birds flee to them next).

4. **Threat variance tracking**: Compute std-dev of recent threat. High-variance fields get +8% priority (anticipating spikes).

5. **In-transit credit**: A drone whose target matches a field counts as "arrived" if we can't tell otherwise — don't pull it. (Already done, but reinforced.)

6. **Slightly relaxed overall move cap**: 40% instead of 33% for non-top fields (momentum + exposure weighting makes moves more reliable now).

## Code Implementation

```python
import math
from typing import List, Dict, Set, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    MOMENTUM_WINDOW = 4
    MOMENTUM_BOOST = 0.12
    VARIANCE_BOOST = 0.08
    EXPOSURE_BOOST = 0.25
    MAX_EXPOSURE_STEPS = 5
    ADJACENCY_BOOST = 0.10
    ADJACENCY_RADIUS = 15.0
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

    def _dist_drone_field(self, drone, field) -> float:
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _dist_fields(self, f1, f2) -> float:
        c1 = self._center(f1); c2 = self._center(f2)
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

    def _effective_threat(self, field) -> float:
        fid = str(field.id)
        hist = self._threat_history.get(fid, [])
        base = field.threat_level

        # Momentum: rising threat boost
        if len(hist) >= 3:
            recent = hist[-3:]
            if recent[-1] > recent[-2] and recent[-2] > recent[-3]:
                base *= (1.0 + self.MOMENTUM_BOOST)

        # Variance: unstable fields get priority (anticipate spikes)
        if len(hist) >= 3:
            mean = sum(hist) / len(hist)
            if mean > 0.01:
                var = sum((x - mean) ** 2 for x in hist) / len(hist)
                std = math.sqrt(var)
                cv = std / mean
                if cv > 0.3:
                    base *= (1.0 + self.VARIANCE_BOOST)

        # Exposure: chronically unprotected fields get urgent
        exposed = self._exposed_steps.get(fid, 0)
        base *= (1.0 + self.EXPOSURE_BOOST * min(exposed, self.MAX_EXPOSURE_STEPS))

        return base

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        # --- Initialize tracking state ---
        if not hasattr(self, '_threat_history'):
            self._threat_history: Dict[str, List[float]] = {}
        if not hasattr(self, '_exposed_steps'):
            self._exposed_steps: Dict[str, int] = {}

        # Update threat history
        for f in environment.fields:
            fid = str(f.id)
            hist = self._threat_history.setdefault(fid, [])
            hist.append(f.threat_level)
            if len(hist) > self.MOMENTUM_WINDOW:
                hist.pop(0)

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            self._exposed_steps = {}
            return

        field_ids: Set[str] = {str(f.id) for f in environment.fields}

        # --- Determine which fields are currently fully protected ---
        current: Dict[int, Optional[str]] = {}
        for d in components:
            current[id(d)] = self._parse_target(d, field_ids)

        cur_count: Dict[str, int] = {}
        for d in components:
            t = current.get(id(d))
            if t:
                cur_count[t] = cur_count.get(t, 0) + 1

        # --- Update exposure tracking ---
        # A field is "exposed" if its current drone count < full protection need
        for f in environment.fields:
            fid = str(f.id)
            if f.threat_level <= 0:
                self._exposed_steps[fid] = 0
                continue
            need = f.drones_for_full_protection
            have = cur_count.get(fid, 0)
            if have < need:
                self._exposed_steps[fid] = self._exposed_steps.get(fid, 0) + 1
            else:
                self._exposed_steps[fid] = 0

        # --- Compute effective threats and sort ---
        eff_threats: Dict[str, float] = {}
        for f in active:
            fid = str(f.id)
            base_eff = self._effective_threat(f)

            # Adjacency boost: if close to a high-threat protected field,
            # birds will flee here next
            adj_bonus = 0.0
            for g in active:
                gid = str(g.id)
                if gid == fid:
                    continue
                if cur_count.get(gid, 0) >= g.drones_for_full_protection:
                    dist = self._dist_fields(f, g)
                    if dist < self.ADJACENCY_RADIUS and g.threat_level > f.threat_level:
                        adj_bonus = max(adj_bonus, self.ADJACENCY_BOOST)
            eff_threats[fid] = base_eff * (1.0 + adj_bonus)

        active.sort(key=lambda f: eff_threats[str(f.id)], reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in active}

        # --- Determine protectable fields ---
        cumulative = 0
        n_full = 0
        for f in active:
            c = f.drones_for_full_protection
            if cumulative + c <= total_drones:
                cumulative += c
                n_full += 1
            else:
                break
        if n_full == 0:
            n_full = 1

        protected_fields = active[:n_full]
        protected_ids = [str(f.id) for f in protected_fields]

        # --- Build target assignment ---
        pool: Set[int] = set(id(d) for d in components)
        target: Dict[str, List[int]] = {str(f.id): [] for f in active}

        # Assign closest drones to each protected field
        for f in protected_fields:
            fid = str(f.id)
            cap = f.drones_for_full_protection
            avail = sorted([d for d in components if id(d) in pool],
                           key=lambda d: self._dist_drone_field(d, f))
            for d in avail:
                if len(target[fid]) >= cap:
                    break
                if id(d) in pool:
                    target[fid].append(id(d))
                    pool.discard(id(d))

        # Surplus: pre-position near the next unprotected field
        if pool:
            next_field = None
            for f in active:
                if str(f.id) not in protected_ids:
                    next_field = f
                    break
            for d in [d for d in components if id(d) in pool]:
                if next_field:
                    best_f = min(protected_fields,
                                 key=lambda pf: self._dist_fields(pf, next_field))
                else:
                    best_f = protected_fields[0]
                target[str(best_f.id)].append(id(d))
                pool.discard(id(d))

        if pool:
            for d in components:
                if id(d) in pool:
                    target[protected_ids[0]].append(id(d))
                    pool.discard(id(d))

        # --- Minimum-change assignment with tiered move caps ---
        final: Dict[int, str] = {}
        claimed: Set[int] = set()

        # Phase 1: Stayers (including in-transit drones already targeting right field)
        for fid in protected_ids:
            for did in target[fid]:
                if current.get(did) == fid:
                    final[did] = fid
                    claimed.add(did)

        # Phase 2: Moves needed
        needed_moves: List[Tuple[int, str]] = []
        for fid in protected_ids:
            for did in target[fid]:
                if did not in claimed:
                    needed_moves.append((did, fid))

        # Sort by target priority (effective threat descending)
        needed_moves.sort(key=lambda m: (
            -eff_threats.get(m[1], 0),
            self._dist_drone_field(
                next(d for d in components if id(d) == m[0]),
                field_by_id[m[1]])
        ))

        # Tiered move cap: top field gets unlimited moves, rest capped
        max_total_moves = max(1, int(total_drones * self.MAX_MOVES_FRACTION))
        applied_non_top = 0
        top_fid = protected_ids[0] if protected_ids else None

        for did, fid in needed_moves:
            if fid == top_fid:
                # Unlimited moves for #1 threat field
                final[did] = fid
                claimed.add(did)
            elif applied_non_top < max_total_moves:
                final[did] = fid
                claimed.add(did)
                applied_non_top += 1
            else:
                # Can't move yet — keep current position
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = fid  # must assign somewhere
                claimed.add(did)

        # Safety net
        for d in components:
            did = id(d)
            if did not in final:
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = protected_ids[0] if protected_ids else str(active[0].id)

        # --- Push to environment ---
        for d in components:
            fid = final.get(id(d))
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")
```