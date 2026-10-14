

Looking at my score history, the 166.3 simple greedy consistently outperforms every "improvement." The critical flaw in all versions: **drones get locked on fields with tiny threats (0.01-0.05) while devastating threats (0.7+) go unprotected**. Since I can't add complex state (it always backfires), I'll make one targeted change: treat threat < 0.05 as effectively dead for lock purposes, freeing those drones. Everything else stays as simple and greedy as the best version.

```py
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    NEARLY_DEAD = 0.05  # treat threat below this as dead for lock decisions

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # Classify drones: locked on active fields vs available
        locked = defaultdict(list)
        available = []

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > self.NEARLY_DEAD:
                    locked[tid].append(drone)
                else:
                    available.append(drone)
            else:
                available.append(drone)

        # Release over-protected drones (keep "protecting" state drones first)
        for fid in list(locked.keys()):
            fld = field_by_id.get(fid)
            if fld is None:
                available.extend(locked[fid])
                del locked[fid]
                continue
            need = fld.drones_for_full_protection
            drones_here = locked[fid]
            if len(drones_here) > need:
                drones_here.sort(key=lambda d: 0 if d.state == "protecting" else 1)
                excess = drones_here[need:]
                locked[fid] = drones_here[:need]
                available.extend(excess)

        # Greedy fill by threat priority, closest drones first
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True
        )

        assignment = {}
        for fid, drones in locked.items():
            for d in drones:
                assignment[id(d)] = fid

        pool = list(available)

        for field in active_fields:
            if not pool:
                break
            fid = field.id
            have = len(locked.get(fid, []))
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                assignment[id(d)] = fid

        # Remaining pool: assign to nearest field still needing drones (partial help)
        if pool:
            remaining = [f for f in active_fields
                         if len(locked.get(f.id, [])) + sum(
                             1 for d in components if assignment.get(id(d)) == f.id
                             and d not in locked.get(f.id, [])
                         ) < f.drones_for_full_protection]
            for d in pool:
                if not remaining:
                    break
                remaining.sort(key=lambda f: (-f.threat_level, self._dist(d.location, f)))
                best = remaining[0]
                assignment[id(d)] = best.id
                need_left = best.drones_for_full_protection - len(locked.get(best.id, [])) - sum(
                    1 for dd in components if assignment.get(id(dd)) == best.id
                    and dd not in locked.get(best.id, [])
                )
                if need_left <= 1:
                    remaining.remove(best)

        # Execute
        for drone in components:
            fid = assignment.get(id(drone))
            if fid is not None:
                gn = f"protecting {fid}"
                environment.assign_group(drone, gn if gn in group_ids else "idle")
            else:
                environment.assign_group(drone, "idle")
```