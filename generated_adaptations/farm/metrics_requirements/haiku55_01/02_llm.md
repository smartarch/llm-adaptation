## Strategy: Threat-Ranked Greedy Allocation with Stickiness

**Core idea:** Rank the threatened fields by threat level and fill them in order. Each field gets up to `drones_for_full_protection` drones, so no field is overprotected. Once the drones run out, the remaining field gets a partial allocation, and any drones left over go idle.

**Steps in each call to `assign_drones`:**

1. **Collect threatened fields.** Keep only fields with `threat_level > 0`, sorted from most to least threatened.
2. **Allocate the top field.** Give it the `drones_for_full_protection` drones closest to its center. This satisfies the requirement that the most threatened field is fully protected by the nearest drones.
3. **Allocate lower-ranked fields with stickiness.** For each subsequent field, first take drones that already target it (to avoid unnecessary switching), ordered by distance. Then fill the remaining capacity with the nearest unassigned drones.
4. **Limit overprotection.** Each field receives at most `drones_for_full_protection` drones.
5. **Prefer full over partial protection.** Because allocation is greedy in threat order, at most one field ends up partially protected: the last one that the available drones reach. All other protected fields are fully protected.
6. **Idle the rest.** Any drone not allocated goes to `"idle"`. Since the fields are filled in order, idle drones only occur when the threatened fields' total requirement is already met, which keeps the idle count low.
7. **Validate group names.** A drone is only assigned to `"protecting {id}"` if that group exists in `group_ids`. Otherwise it falls back to `"idle"`.

**Trade-off:** The top field uses pure distance so its protectors are the closest drones. Lower fields prefer drones already en route or on station, which keeps at least half of the drones on a consistent field over time.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    @classmethod
    def _distance(cls, drone, field):
        cx, cy = cls._field_center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        drones = list(components)

        # Threatened fields, most threatened first
        fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: -f.threat_level,
        )

        # drone -> field id mapping (identity-based to be safe with component objects)
        plan = {}  # id(drone) -> field id
        remaining = list(drones)

        for rank, field in enumerate(fields):
            if not remaining:
                break

            cap = max(1, int(round(field.drones_for_full_protection)))

            if rank == 0:
                # Most threatened field: closest drones only
                chosen = sorted(remaining, key=lambda d: self._distance(d, field))[:cap]
            else:
                # Stickiness: prefer drones already targeting this field, then nearest
                sticky = sorted(
                    [d for d in remaining if d.target_id == field.id],
                    key=lambda d: self._distance(d, field),
                )
                others = sorted(
                    [d for d in remaining if d.target_id != field.id],
                    key=lambda d: self._distance(d, field),
                )
                chosen = (sticky + others)[:cap]

            chosen_ids = {id(d) for d in chosen}
            for d in chosen:
                plan[id(d)] = field.id
            remaining = [d for d in remaining if id(d) not in chosen_ids]

        # Apply assignments
        for drone in drones:
            field_id = plan.get(id(drone))
            if field_id is not None:
                group = f"protecting {field_id}"
                if group in valid_groups:
                    environment.assign_group(drone, group)
                    continue
            environment.assign_group(drone, "idle")
```