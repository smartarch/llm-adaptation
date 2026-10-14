## Revised strategy: marginal-value greedy allocation

The previous version had three weaknesses:

1. **Leftover drones were dumped on the top field.** That field was often already fully protected, so the extra drones added nothing.
2. **Partially covered fields were not topped up in a principled way.** Pass 2 gave them drones in threat order, but without weighing how much each additional drone helps.
3. **Surplus drones on fully protected fields were released, but not reused well.** They were pooled and then dumped on the top field.

The new approach models the benefit of each field as a function of its drone count and allocates drones one at a time to the field that gains the most from the next drone.

- **Value model:** A field's value is `threat × (0.5 × min(c, need)/need + 0.5 × [c ≥ need])`. Partial coverage earns credit in proportion to coverage, and full protection earns an extra bonus because birds only flee when a field is fully protected. Marginal gain is the difference between `value(c+1)` and `value(c)`.
- **Stable core:** Drones already protecting or moving to a field keep their assignment, up to `need`. Only surplus drones beyond `need` are released, so no unnecessary flights are introduced.
- **Greedy filling:** Each free drone goes to the field with the largest marginal gain. Ties are broken by threat order, and the closest free drone is chosen for that field, which minimizes flight time.
- **No wasted drones:** Once every field is fully covered, marginal gain is zero. Remaining drones then go to the highest-threat field, as before.

I have not run this in the simulator, so the 150.7 baseline should be re-measured to confirm the improvement.

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

    @staticmethod
    def _value(threat, need, count):
        # Partial coverage earns credit proportional to coverage;
        # full protection earns an extra bonus (birds only flee when fully protected).
        covered = min(count, need) / need
        full = 1.0 if count >= need else 0.0
        return threat * (0.5 * covered + 0.5 * full)

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

        # Keep up to `need` reserved drones per field (protecting ones first, then closest);
        # release surplus to the free pool.
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

        # Greedy allocation: each free drone goes to the field with the largest marginal gain
        while free:
            best_field = None
            best_gain = 0.0
            for f in fields:  # threat order, so ties favour higher threat
                n = need[f.id]
                c = count[f.id]
                gain = (self._value(f.threat_level, n, c + 1)
                        - self._value(f.threat_level, n, c))
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_field = f

            if best_field is None:
                # Every field is fully covered: reinforce the highest-threat field
                best_field = fields[0]

            free.sort(key=lambda d: self._dist(d, best_field))
            drone = free.pop(0)
            assignment[id(drone)] = best_field.id
            count[best_field.id] += 1

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")
```