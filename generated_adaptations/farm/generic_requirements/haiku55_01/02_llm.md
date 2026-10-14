## Strategy: Threat-Ranked Greedy Allocation with Hysteresis

**Core idea:** Allocate drones to threatened fields in descending threat order, giving each field exactly the number of drones needed for full protection. This satisfies the requirements as follows:

1. **Most threatened field is fully protected first.** It is the first field processed and gets `drones_for_full_protection` drones before any other field is considered.
2. **Closest drones protect the most threatened field.** For the top-ranked field, drones are sorted purely by distance to the field center.
3. **No overprotection.** Each field receives at most `drones_for_full_protection` drones.
4. **Few idle drones.** Drones are only idle when the total protection demand of all threatened fields is smaller than the fleet. Otherwise, leftover drones are used on the next field in the ranking.
5. **Prefer full protection over many partial ones.** Fields are filled in order, so at most one field ends up partially protected (the last one that receives drones). Lower-ranked fields are left unprotected rather than spread thin.
6. **Stability.** For lower-ranked fields, a drone that is already heading to the field gets a distance bonus (hysteresis). This reduces needless switching between fields. The top field uses pure distance so the closest-drone rule holds strictly.

**Changes from a naive version:** The hysteresis bonus is applied only to non-top fields, so it never overrides the "closest drones for the most threatened field" requirement. The bonus is scaled to the farm size so it works regardless of coordinate units.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Threat-ranked greedy allocation with hysteresis.

    - Threatened fields are processed in descending threat order.
    - Each field receives up to `drones_for_full_protection` drones, so the
      most threatened fields are fully protected first and never overprotected.
    - The most threatened field gets the closest drones (pure distance).
    - Lower-ranked fields prefer drones already heading to them (hysteresis),
      which reduces field switching.
    - Leftover drones are only idle if all threatened fields are already covered.
    """

    HYSTERESIS_FRACTION = 0.1  # fraction of farm span used as stickiness bonus

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone, field):
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _farm_span(self, fields):
        if not fields:
            return 1.0
        left = min(f.left for f in fields)
        right = max(f.right for f in fields)
        top = min(f.top for f in fields)
        bottom = max(f.bottom for f in fields)
        span = math.hypot(right - left, bottom - top)
        return span if span > 0 else 1.0

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        all_fields = list(environment.fields)
        threatened = [f for f in all_fields if f.threat_level > 0]
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        hysteresis = self.HYSTERESIS_FRACTION * self._farm_span(all_fields)

        assignment = {}  # drone index -> group name
        available = list(range(len(drones)))

        for rank, field in enumerate(threatened):
            if not available:
                break

            need = max(1, int(field.drones_for_full_protection))

            if rank == 0:
                # Most threatened field: strictly the closest drones.
                def key(i, field=field):
                    return self._distance(drones[i], field)
            else:
                # Lower-ranked fields: prefer drones already targeting them.
                def key(i, field=field):
                    bonus = hysteresis if drones[i].target_id == field.id else 0.0
                    return self._distance(drones[i], field) - bonus

            ranked = sorted(available, key=key)
            chosen = ranked[:need]
            group = f"protecting {field.id}"
            for i in chosen:
                assignment[i] = group

            chosen_set = set(chosen)
            available = [i for i in available if i not in chosen_set]

        # Any drones not needed for protection go idle.
        for i in available:
            assignment[i] = "idle"

        # Every drone must be explicitly assigned.
        for i, drone in enumerate(drones):
            group = assignment.get(i, "idle")
            environment.assign_group(drone, group)
```