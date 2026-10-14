## Analysis of the previous result

The marginal-value version scored worse (189.0 vs. 150.7). I think there are three reasons:

1. **Spreading drones thin.** The greedy allocator gave each field a share of drones in proportion to partial coverage. Birds only flee when a field is fully protected, so a field at 60% coverage still takes damage. Several fields at partial coverage cause more damage than one field fully protected and the rest left alone.
2. **Under-weighted full protection.** The linear partial credit (0.5 × coverage) was large relative to the full-protection bonus. The optimizer preferred many partial fields over completing the top ones.
3. **Distance ignored in the choice of field.** The greedy step picked fields by value gain, not by how quickly a drone could arrive. Drones flying long distances protect nothing during the flight.

## Revised strategy: strict threat priority with concentrated reinforcement

I return to the threat-ordered structure that scored best, and change two behaviours:

- **Strict priority.** Fields are processed from highest to lowest threat. If the current field can be fully covered with the kept drones plus the free pool, it is covered and we continue. If it cannot, all remaining free drones are concentrated on it, closest first, and lower-threat fields get nothing new. This completes the most threatened field as early as possible, rather than spreading drones so that nothing is fully protected.
- **Sticky core and leftovers.** Drones already protecting or moving to a field keep their assignment, up to `need`. Surplus drones are released to the pool. Any drones left over after all fields are fully covered reinforce the highest-threat field.

I have not run this in the simulator, so the result needs to be measured against the 150.7 baseline.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _dist(drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)

        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        if not fields:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        cand_ids = {f.id for f in fields}
        need = {f.id: max(1, int(f.drones_for_full_protection)) for f in fields}

        # Drones already heading to / protecting a candidate field are reserved there
        reserved = {f.id: [] for f in fields}
        free = []
        for d in drones:
            if d.target_id in cand_ids and d.state in ("moving_to_field", "protecting"):
                reserved[d.target_id].append(d)
            else:
                free.append(d)

        assignment = {}  # id(drone) -> field id
        count = {}

        # Keep up to `need` reserved drones per field (protecting first, then closest).
        # Surplus goes back into the free pool.
        for f in fields:
            kept = sorted(
                reserved[f.id],
                key=lambda d: (d.state != "protecting", self._dist(d, f)),
            )
            keep, surplus = kept[:need[f.id]], kept[need[f.id]:]
            for d in keep:
                assignment[id(d)] = f.id
            count[f.id] = len(keep)
            free.extend(surplus)

        def take_closest(field, k):
            nonlocal free
            free.sort(key=lambda d: self._dist(d, field))
            taken, free = free[:k], free[k:]
            for d in taken:
                assignment[id(d)] = field.id
            count[field.id] += len(taken)

        # Pass 1: strict threat priority.
        # Complete each field in order. If the current field cannot be completed,
        # concentrate every remaining free drone on it and stop, so lower-threat
        # fields do not dilute coverage of the most threatened one.
        for f in fields:
            deficit = need[f.id] - count[f.id]
            if deficit <= 0:
                continue
            if deficit <= len(free):
                take_closest(f, deficit)
            else:
                take_closest(f, len(free))
                break

        # Leftovers (only when every field is already complete): reinforce the top field
        if free:
            take_closest(fields[0], len(free))

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")
```