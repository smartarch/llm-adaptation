

The 0.05 threshold was a massive breakthrough! Now I'll build on that foundation with targeted refinements:

1. **Prefer drones already near a field**: When selecting available drones for a deficit, prioritize ones already heading that way or hovering nearby (minimizing transit time).
2. **Better partial protection**: Distribute remaining drones proportionally to `threat × deficit` rather than just "nearest" — this ensures high-threat fields get more partial coverage.
3. **Cleaner assignment accounting**: Avoid double-counting bugs in the partial-protection loop.
4. **Slightly lower threshold (0.03)**: Be a bit more conservative about freeing drones, since the 0.05 result already showed diminishing returns from freeing too aggressively.

```py
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    NEARLY_DEAD = 0.03

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Classify drones ---
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

        # --- Release over-protected drones ---
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

        # --- Build assignment map from locked ---
        assignment = {}
        for fid, drones in locked.items():
            for d in drones:
                assignment[id(d)] = fid

        # --- Greedy full-protection fill by threat priority ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True
        )

        pool = list(available)

        for field in active_fields:
            if not pool:
                break
            fid = field.id
            have = len(locked.get(fid, [])) + sum(
                1 for d in components if assignment.get(id(d)) == fid
                and d not in locked.get(fid, [])
            )
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue

            # Sort available: prefer those already heading here, then by distance
            pool.sort(key=lambda d: (
                0 if d.target_id == fid else 1,  # already heading here
                self._dist(d.location, field)     # then closest
            ))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                assignment[id(d)] = fid

        # --- Partial protection: distribute remaining drones by threat × deficit ---
        if pool and active_fields:
            # Compute current counts including new assignments
            cur_count = defaultdict(int)
            for fid, drones in locked.items():
                cur_count[fid] = len(drones)
            for d in components:
                fid = assignment.get(id(d))
                if fid is not None:
                    cur_count[fid] += 1

            # Build deficit list
            deficits = []
            for field in active_fields:
                fid = field.id
                need = field.drones_for_full_protection
                have = cur_count[fid]
                def_val = need - have
                if def_val > 0:
                    deficits.append((field, def_val))

            if deficits:
                # Proportional distribution by threat * deficit
                total_weight = sum(f.threat_level * d for f, d in deficits)
                if total_weight > 0:
                    allocations = {}
                    for field, def_val in deficits:
                        w = field.threat_level * def_val
                        share = int(pool.__len__() * w / total_weight)
                        allocations[field.id] = min(share, def_val)

                    # Assign allocated drones
                    remaining_pool = list(pool)
                    for field, def_val in deficits:
                        fid = field.id
                        to_give = allocations.get(fid, 0)
                        if to_give <= 0 or not remaining_pool:
                            continue
                        remaining_pool.sort(key=lambda d: self._dist(d.location, field))
                        take = remaining_pool[:to_give]
                        remaining_pool = remaining_pool[to_give:]
                        for d in take:
                            assignment[id(d)] = fid

                    # Leftover from rounding: assign one-by-one to highest threat*deficit
                    while remaining_pool:
                        best_f = None
                        best_s = -1
                        for field, def_val in deficits:
                            fid = field.id
                            cur = cur_count[fid] + sum(1 for d in components if assignment.get(id(d)) == fid and d not in locked.get(fid, []))
                            still_need = field.drones_for_full_protection - cur
                            if still_need <= 0:
                                continue
                            s = field.threat_level * still_need - self._dist(remaining_pool[0].location, field) * 0.01
                            if s > best_s:
                                best_s = s
                                best_f = fid
                        if best_f is None:
                            break
                        d = remaining_pool.pop(0)
                        assignment[id(d)] = best_f
                        cur_count[best_f] += 1

        # --- Execute ---
        for drone in components:
            fid = assignment.get(id(drone))
            if fid is not None:
                gn = f"protecting {fid}"
                if gn in group_ids:
                    environment.assign_group(drone, gn)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
```