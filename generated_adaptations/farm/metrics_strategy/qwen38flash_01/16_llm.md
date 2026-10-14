

Looking at the score history carefully, my two best results (166.3) used simple greedy that processes fields top-down by threat. The 177.7 regression came from a "grace period" on dead fields that actually caused drones to go idle (because the `"protecting {fid}"` group doesn't exist for dead fields, so the group check failed).

**Key insight for improvement**: The problem states partial protection is *weak* but full protection makes birds flee entirely. This creates a **threshold effect** — a field at need-1 drones benefits enormously from its final drone (completes protection), while a field at 0 drones barely benefits from its first drone. My greedy was assigning equally to all deficits, wasting drones on hopeless fields.

**New strategy**: Use **marginal-value greedy** — at each step, pick the single assignment that provides the most marginal protection value, then give it the closest available drone. Fields near full-completion get prioritized over fields at 0. This ensures we complete fields fast rather than spreading thin.

```py
import math
import heapq
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    PARTIAL_FACTOR = 0.12  # partial protection effectiveness relative to full

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Lock drones on active fields, release the rest ---
        locked_by_field = defaultdict(list)
        available = []

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > 0:
                    locked_by_field[tid].append(drone)
                else:
                    available.append(drone)
            else:
                available.append(drone)

        # Release over-protected drones (prefer keeping 'protecting' state)
        for fid in list(locked_by_field.keys()):
            fld = field_by_id.get(fid)
            if fld is None:
                available.extend(locked_by_field[fid])
                del locked_by_field[fid]
                continue
            need = fld.drones_for_full_protection
            drones_here = locked_by_field[fid]
            if len(drones_here) > need:
                drones_here.sort(key=lambda d: 0 if d.state == "protecting" else 1)
                excess = drones_here[need:]
                locked_by_field[fid] = drones_here[:need]
                available.extend(excess)

        # --- Current drone count per field ---
        count = {f.id: len(locked_by_field[f.id]) for f in environment.fields}

        # Active fields sorted by threat
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_field_ids = set(f.id for f in active_fields)

        # --- Marginal-value greedy assignment ---
        # For each field needing drones, compute marginal value of next drone.
        # Use a max-heap (negate for min-heap) keyed by marginal value.
        # Pop the best assignment, give it the closest available drone, repeat.

        assignment = {}  # drone_id -> field_id
        for fid, drones in locked_by_field.items():
            for d in drones:
                assignment[id(d)] = fid

        # Build initial heap entries
        # marginal_value(k->k+1) for a field with need N and threat T:
        #   if k+1 == N: T * (1 - PARTIAL_FACTOR * k/N)   (big jump to full protection)
        #   else:       T * PARTIAL_FACTOR / N              (small partial benefit)
        heap = []
        field_info = {f.id: f for f in active_fields}

        for field in active_fields:
            fid = field.id
            need = field.drones_for_full_protection
            k = count[fid]
            if k >= need:
                continue
            # Compute marginal value of drone k -> k+1
            if k + 1 == need:
                mv = field.threat_level * (1.0 - self.PARTIAL_FACTOR * k / need)
            else:
                mv = field.threat_level * self.PARTIAL_FACTOR / need
            if mv > 0:
                heapq.heappush(heap, (-mv, fid))

        pool = list(available)

        while heap and pool:
            neg_mv, fid = heapq.heappop(heap)
            field = field_info[fid]
            if count[fid] >= field.drones_for_full_protection:
                continue  # already satisfied
            if not pool:
                break

            # Assign closest drone from pool to this field
            pool.sort(key=lambda d: self._dist(d.location, field))
            d = pool.pop(0)
            assignment[id(d)] = fid
            count[fid] += 1

            # Push next marginal value for this field
            need = field.drones_for_full_protection
            k = count[fid]
            if k < need:
                if k + 1 == need:
                    mv = field.threat_level * (1.0 - self.PARTIAL_FACTOR * k / need)
                else:
                    mv = field.threat_level * self.PARTIAL_FACTOR / need
                if mv > 0:
                    heapq.heappush(heap, (-mv, fid))

        # Any remaining pool drones: give to nearest field with any deficit
        if pool:
            remaining_fields = [f for f in active_fields
                                if count[f.id] < f.drones_for_full_protection]
            remaining_fields.sort(key=lambda f: f.threat_level, reverse=True)
            for d in pool:
                if not remaining_fields:
                    break
                # Assign to nearest still-need field with highest threat
                remaining_fields.sort(key=lambda f: (self._dist(d.location, f), -f.threat_level))
                fld = remaining_fields[0]
                if count[fld.id] < fld.drones_for_full_protection:
                    assignment[id(d)] = fld.id
                    count[fld.id] += 1
                    if count[fld.id] >= fld.drones_for_full_protection:
                        remaining_fields.remove(fld)

        # --- Execute ---
        for drone in components:
            did = id(drone)
            fid = assignment.get(did)
            if fid is not None:
                gn = f"protecting {fid}"
                if gn in group_ids:
                    environment.assign_group(drone, gn)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
```