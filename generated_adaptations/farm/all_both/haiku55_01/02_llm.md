## Strategy: Threat-ordered allocation with sticky tie-breaking

1. **Rank the threats.** Consider only fields with `threat_level > 0`, sorted by descending threat (ties broken by id). The top field is the most threatened one.
2. **Full-protection pass.** Walk the ranked fields and give each one exactly `drones_for_full_protection` drones, so no field is overprotected.
   - For the top field, drones are chosen strictly by distance to the field center, so the closest drones protect the most threatened field.
   - If the top field cannot be fully covered with the drones available, the pass stops. This keeps lower-ranked fields from taking drones the top field needs.
   - For lower fields, drones already protecting that field get a distance bonus. This reduces unnecessary reassignments.
3. **Leftover pass.** Any remaining drones go to the highest-ranked field that is still not fully protected. This avoids idle drones, and it creates at most one partially protected field, so the strategy does not spread drones thinly across many fields.
4. **Idle remainder.** Drones that are still unassigned, for example when no field needs them, go to the `"idle"` group.

Every drone is assigned exactly once. Group names are checked against `group_ids`, and a drone falls back to idle if its target group is not valid.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    # Distance bonus (in map units) for drones already protecting a non-top field.
    # Reduces unnecessary reassignments; the top field uses strict distance.
    STICKY_BONUS = 10.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, drone, field):
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _is_protecting(self, drone, field):
        return drone.state in ("moving_to_field", "protecting") and drone.target_id == field.id

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        drones = list(components)

        fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: (-f.threat_level, str(f.id)),
        )

        remaining = list(drones)
        allocation = {}  # field.id -> list of drones

        def pick(field, k, strict):
            def key(d):
                d_dist = self._dist(d, field)
                if not strict and self._is_protecting(d, field):
                    d_dist -= self.STICKY_BONUS
                return d_dist

            chosen = sorted(remaining, key=key)[:k]
            for d in chosen:
                remaining.remove(d)
                allocation.setdefault(field.id, []).append(d)
            return chosen

        # Pass 1: full protection, highest threat first, no overprotection.
        for idx, field in enumerate(fields):
            need = max(1, int(field.drones_for_full_protection))
            if len(remaining) >= need:
                pick(field, need, strict=(idx == 0))
            elif idx == 0:
                # The most threatened field cannot be fully covered; stop so that
                # lower fields do not take the drones it needs. Leftovers go to it below.
                break

        # Pass 2: leftover drones go to the highest-ranked field still not fully protected.
        for field in fields:
            if not remaining:
                break
            need = max(1, int(field.drones_for_full_protection))
            current = len(allocation.get(field.id, []))
            missing = need - current
            if missing > 0:
                pick(field, min(missing, len(remaining)), strict=(field is fields[0]))

        # Apply group assignments.
        field_by_id = {f.id: f for f in fields}
        drone_group = {}
        for field_id, assigned in allocation.items():
            group = f"protecting {field_id}"
            if group in valid_groups:
                for d in assigned:
                    drone_group[id(d)] = group

        idle_group = "idle"
        for d in drones:
            group = drone_group.get(id(d), idle_group)
            if group not in valid_groups:
                group = idle_group
            environment.assign_group(d, group)
```