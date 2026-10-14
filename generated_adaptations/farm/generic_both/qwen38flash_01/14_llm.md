

## Strategy Description

The score regressed 59 → 68.3 due to over-engineering: the cooldown and atomicity constraints made the system too slow to react to threat spikes and too reluctant to pull drones, leaving high-threat fields under-defended.

Looking at the trajectory (148 → 68 → 83 → **59** → 68), the clear winner is the **simple greedy + minimum-change + concentration** approach. The principle: *react instantly, move minimally, never partially defend*.

**Final refined strategy:**

1. **Immediate reaction**: Sort fields by threat; assign drones to top fields first. No hysteresis, no cooldown — threat changes must be answered this step.

2. **Full-protection capacity calc**: Compute how many top fields can be *fully* protected with all drones. If even the top field is too expensive to fully protect, **concentrate all drones on it** (one fully defended field ≫ many half-defended ones).

3. **Minimum-change matching**: A drone already on the field it would be assigned to stays put. This eliminates unnecessary transit without a cooldown.

4. **Smart surplus as reserves**: Surplus drones (beyond what's needed to fully protect the chosen set) are distributed **round-robin across the protected fields** rather than dumped on the top one. This way, if any field's threat spikes, it already has nearby reserves to fill gaps immediately, cutting response time.

5. **Robust target parsing**: Handle various target-id encodings defensively so we never misread a drone's current location (which causes spurious reassignments).

6. **No partial defense**: Fields outside the protectable set get zero drones; that's a deliberate design — partial defense wastes drones that could finish protecting a real field.

This is essentially the 59.0 algorithm with one meaningful addition (distributed reserves instead of top-field surplus), which directly reduces damage spikes when threats shift.

## Code Implementation

```python
import math
from typing import List, Dict, Set, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

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

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort by threat descending — priority order for protection
        active.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in active}
        field_ids: Set[str] = set(field_by_id.keys())

        # --- Current target of each drone ---
        current: Dict[int, Optional[str]] = {}
        for d in components:
            current[id(d)] = self._parse_target(d, field_ids)

        # --- How many top fields can be FULLY protected? ---
        cumulative = 0
        n_full = 0
        for f in active:
            c = f.drones_for_full_protection
            if cumulative + c <= total_drones:
                cumulative += c
                n_full += 1
            else:
                break
        # If we can't fully protect even the top field, concentrate on it
        if n_full == 0:
            n_full = 1

        # Fields we will fully protect: active[0 .. n_full-1]
        protected_fields = active[:n_full]
        protected_ids = [str(f.id) for f in protected_fields]

        # --- Build target assignment ---
        pool: Set[int] = set(id(d) for d in components)
        target: Dict[str, List[int]] = {str(f.id): [] for f in active}

        # Pass 1: assign enough drones to fully protect each protected field,
        # closest drones first (greedy by field priority, then distance).
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

        # Pass 2: distribute surplus as reserves round-robin across protected
        # fields (so any field getting a threat spike has nearby reserves).
        # If no protected fields (shouldn't happen since n_full >= 1), use top.
        reserve_targets = protected_fields if protected_fields else active
        rr = 0
        for d in [d for d in components if id(d) in pool]:
            f = reserve_targets[rr % len(reserve_targets)]
            fid = str(f.id)
            target[fid].append(id(d))
            pool.discard(id(d))
            rr += 1

        # Any still-unassigned (should be none) → top field
        if pool:
            top_fid = protected_ids[0] if protected_ids else str(active[0].id)
            for d in components:
                if id(d) in pool:
                    target[top_fid].append(id(d))
                    pool.discard(id(d))

        # --- Minimum-change: prefer keeping drones where they already are ---
        # Build the set of (drone → target_field). Then, if a drone is already
        # targeting field X and field X still wants it, keep it.
        # We construct the final assignment by:
        #   1. For each field, mark which currently-there drones are in its target list → those stay.
        #   2. For target slots not yet filled by stayers, pick from the
        #      globally-unclaimed drones, preferring those currently on fields
        #      with the most surplus (so we minimize damage to the donor).
        final: Dict[int, str] = {}
        claimed: Set[int] = set()

        # Stayers first
        for fid in protected_ids:
            for did in target[fid]:
                if current.get(did) == fid:
                    final[did] = fid
                    claimed.add(did)

        # For each field, fill remaining target slots with unclaimed drones.
        # Source selection: prefer drones currently on fields that have MORE
        # than their current target needs (i.e., a safe donor), then by distance.
        # Compute how many drones each field currently has and how many we're
        # trying to put there in the target — surplus = current - target_kept.
        for fid in protected_ids:
            need = len(target[fid]) - sum(1 for d in target[fid]
                                          if final.get(d) == fid)
            if need <= 0:
                continue
            # Compute donor fields: any field (in field_ids or None) with more
            # currently-there drones than we plan to keep there.
            # Keep-count per field = number of its target drones that stay.
            keep_per_field: Dict[Optional[str], int] = {}
            for f in protected_ids:
                keep_per_field[f] = sum(1 for did in target[f]
                                        if final.get(did) == f)
            cur_count: Dict[Optional[str], int] = {}
            for d in components:
                c = current.get(id(d))
                cur_count[c] = cur_count.get(c, 0) + 1

            # Candidate donors: drones not yet claimed, grouped by their current field
            # with surplus available.
            donors: List[int] = []
            surplus_map: Dict[Optional[str], int] = {}
            for c, cnt in cur_count.items():
                want = keep_per_field.get(c, 0)
                surplus_map[c] = cnt - want

            unclaimed_drones = [d for d in components
                                if id(d) not in claimed and id(d) in target[fid]]
            # Sort by: (donor_surplus descending, distance to this field ascending)
            # So we pull from a field that has plenty, and pick the closest.
            def key_fn(d):
                c = current.get(id(d))
                s = surplus_map.get(c, 0)
                return (-s, self._dist(d, field_by_id[fid]))
            unclaimed_drones.sort(key=key_fn)
            for d in unclaimed_drones:
                if need <= 0:
                    break
                final[id(d)] = fid
                claimed.add(id(d))
                need -= 1

            # If still need (drone was supposed to be in target[fid] but
            # wasn't unclaimed), fall back to any unclaimed drone
            if need > 0:
                others = sorted([d for d in components if id(d) not in claimed],
                                key=lambda d: self._dist(d, field_by_id[fid]))
                for d in others:
                    if need <= 0:
                        break
                    final[id(d)] = fid
                    claimed.add(id(d))
                    need -= 1

        # Drones not in any target list but still unclaimed (surplus reserves
        # were added to target lists above, so this shouldn't trigger — but
        # safety) → put on protected field with most reserves room.
        for d in components:
            if id(d) not in final:
                final[id(d)] = protected_ids[0] if protected_ids else str(active[0].id)

        # --- Push final assignment to environment ---
        for d in components:
            fid = final.get(id(d))
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")
```