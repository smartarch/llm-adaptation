

Looking at my score history, my simplest approach (166.3) was best. Every "improvement" introduced oscillation or bugs. The core problem I now identify: **assignment instability**. Tiny threat fluctuations cause reassignment every step, so drones spend all their time in transit and never actually protect anything.

**Root cause fix:** A drone already assigned to a field with threat > 0 should NEVER be reassigned. It should only be released when the field is truly dead (threat = 0). Among free drones, assign greedily by threat priority using closest drones. If a drone can't provide full protection to any field, keep it at its current (even dead) field rather than idling or creating oscillation.

```py
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dead_count = {}  # field_id -> consecutive steps at threat=0

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Track how long each field has been dead ---
        for field in environment.fields:
            if field.threat_level > 0:
                self._dead_count[field.id] = 0
            else:
                self._dead_count[field.id] = self._dead_count.get(field.id, 0) + 1

        # --- Phase 1: Lock drones on active fields ---
        # A drone targeting an active field stays. Period. No exceptions.
        locked = {}  # field_id -> [drones]
        released = []  # drones that are free to be reassigned

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > 0:
                    # ACTIVE FIELD - lock the drone here, no matter what
                    locked.setdefault(tid, []).append(drone)
                elif self._dead_count[tid] <= 1:
                    # Just turned dead - give it one grace step (avoids flicker)
                    locked.setdefault(tid, []).append(drone)
                else:
                    # Truly dead - release
                    released.append(drone)
            else:
                # No valid target or idle
                released.append(drone)

        # --- Phase 2: Over-protection release ---
        # If a field has more locked drones than needed, release excess
        for fid in list(locked.keys()):
            fld = field_by_id.get(fid)
            if fld is None:
                released.extend(locked[fid])
                del locked[fid]
                continue
            need = fld.drones_for_full_protection
            drones_here = locked[fid]
            if len(drones_here) > need:
                # Keep those already protecting, release movers
                drones_here.sort(key=lambda d: 0 if d.state == "protecting" else 1)
                excess = drones_here[need:]
                locked[fid] = drones_here[:need]
                released.extend(excess)

        # --- Phase 3: Greedy full-protection fill ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True
        )

        pool = list(released)
        new_assignments = {}  # drone_id -> field_id (for newly assigned)

        for field in active_fields:
            if not pool:
                break
            fid = field.id
            have = len(locked.get(fid, []))
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue
            # Closest drones first
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                new_assignments[id(d)] = fid

        # --- Phase 4: Partial protection for remaining deficits ---
        for field in active_fields:
            if not pool:
                break
            fid = field.id
            have = len(locked.get(fid, [])) + sum(1 for d in components if new_assignments.get(id(d)) == fid)
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                new_assignments[id(d)] = fid

        # --- Phase 5: Remaining drones - assign to nearest field needing drones or keep on dead field ---
        if pool:
            for d in pool:
                best_fid = None
                best_score = -1.0
                for field in active_fields:
                    fid = field.id
                    have = len(locked.get(fid, [])) + sum(1 for dd in components if new_assignments.get(id(dd)) == fid)
                    need = field.drones_for_full_protection
                    if have >= need:
                        continue
                    # Score: higher threat and closer = better
                    score = field.threat_level - self._dist(d.location, field) * 0.01
                    if score > best_score:
                        best_score = score
                        best_fid = fid
                if best_fid:
                    new_assignments[id(d)] = best_fid
                elif d.target_id and d.target_id in field_by_id:
                    # Keep on current dead field (it costs nothing to hover there)
                    new_assignments[id(d)] = d.target_id

        # --- Execute ---
        for drone in components:
            did = id(drone)
            if did in new_assignments:
                fid = new_assignments[did]
            else:
                # Was locked
                fid = drone.target_id
            if fid and f"protecting {fid}" in group_ids:
                environment.assign_group(drone, f"protecting {fid}")
            else:
                environment.assign_group(drone, "idle")
```