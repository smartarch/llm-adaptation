## Strategy: Threat-Ordered Greedy Allocation with Stickiness

1. **Rank the threats.** Collect fields with `threat_level > 0` and sort them by threat, highest first.
2. **Fill each field to full protection, in priority order.** For each field, take `drones_for_full_protection` drones from the unassigned pool. Candidates are ordered so that drones already committed to that field (state `protecting` or `moving_to_field` with a matching `target_id`) come first, then by distance to the field center. This keeps drones in place and avoids needless flights.
3. **Never leave drones idle while a field needs them.** Any drones left after a field is fully covered flow to the next most threatened field. A field may receive only part of its requirement, which still beats no protection. Drones go to `idle` only when every threatened field is already fully covered.
4. **Assign every drone exactly once**, and only to group names present in `group_ids`.

Field centers are computed from `left`, `right`, `top`, and `bottom`. Distances are Euclidean, using the drone's `location.x` and `location.y`.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    @staticmethod
    def _distance(drone, point):
        dx = drone.location.x - point[0]
        dy = drone.location.y - point[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        valid = set(group_ids)

        # 1. Threatened fields, highest threat first
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        unassigned = list(drones)
        assignment = {}

        # 2./3. Fill fields in priority order, prioritising the closest drones
        #       and those already committed to the field (stickiness).
        for field in fields:
            group = f"protecting {field.id}"
            if group not in valid:
                continue
            need = int(field.drones_for_full_protection)
            if need <= 0 or not unassigned:
                continue

            center = self._field_center(field)

            def sort_key(d, fid=field.id, c=center):
                committed = (d.target_id == fid and d.state in ("protecting", "moving_to_field"))
                return (0 if committed else 1, self._distance(d, c))

            candidates = sorted(unassigned, key=sort_key)
            chosen = candidates[:need]
            for d in chosen:
                assignment[d] = group
            chosen_set = set(chosen)
            unassigned = [d for d in unassigned if d not in chosen_set]

        # 4. Leftover drones: idle only if no threatened field still needs them
        for d in unassigned:
            assignment[d] = "idle"

        # 5. Every drone is assigned exactly once
        for d in drones:
            environment.assign_group(d, assignment.get(d, "idle"))
```