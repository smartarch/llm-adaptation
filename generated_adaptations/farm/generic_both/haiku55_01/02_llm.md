## Strategy: Priority-Ordered Full Coverage with Sticky Assignments

**Core idea:** Process fields from most to least threatened. Give each field exactly the number of drones it needs for full protection, choosing the closest available drones. Skip any field that cannot be fully covered with the drones still free. Use leftover drones for at most one partially covered field, and send any remaining drones to idle.

**Steps in each call to `assign_drones`:**

1. **Collect candidates.** Keep only fields with `threat_level > 0`, sorted by threat in descending order. Field centers are computed from `left/right/top/bottom`.
2. **Full protection, highest threat first.** For each field, take `need = drones_for_full_protection` (at least 1). If enough unassigned drones remain, choose the `need` best drones and assign them. The ranking is by distance to the field center, with a small bonus (a distance discount) for drones already heading to or protecting that field. This favours the closest drones while avoiding unnecessary reassignments. If there are not enough drones, skip the field so no field is left partially covered by default.
3. **Partial coverage for leftovers only.** If drones remain after step 2, they go to the highest-threat field that is still uncovered, capped at its requirement so it is never overprotected. This is the only partially protected field, which keeps partial coverage to a minimum.
4. **Idle remainder.** Any drone still unassigned goes to `"idle"`. Because of step 3, this only happens when every uncovered field is already at its cap, or when no threatened fields exist.

**How the requirements are addressed:**
- The most threatened field is always fully protected if the drone count allows it.
- Its drones are the closest ones (with a stickiness tie-break).
- No field receives more drones than `drones_for_full_protection`.
- Drones are kept on fields they already target when the distance difference is small, which limits switching.
- Idle drones are minimized, since drones fill every threatened field they can fully cover.
- Partial protection is limited to at most one field.

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Priority-ordered full-coverage strategy:
      1. Fields with threat > 0 are processed from most to least threatened.
      2. Each field receives exactly `drones_for_full_protection` drones
         (closest first, with a stickiness bonus for drones already on it),
         but only if enough free drones remain (no partial coverage by default).
      3. Leftover drones partially cover at most one field (the most threatened
         uncovered one), capped at its requirement to avoid overprotection.
      4. Any remaining drones are sent to "idle".
    """

    STICKY_BONUS = 2.0  # distance discount for drones already heading to / protecting the field

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    @staticmethod
    def _distance(drone, cx, cy):
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _score(self, drone, field):
        cx, cy = self._field_center(field)
        d = self._distance(drone, cx, cy)
        if drone.target_id == field.id and drone.state in ("moving_to_field", "protecting"):
            d -= self.STICKY_BONUS
        return d

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        remaining = list(drones)

        threatened = [f for f in environment.fields if f.threat_level > 0]
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        def group_name(field):
            return f"protecting {field.id}"

        def need_of(field):
            return max(1, int(field.drones_for_full_protection))

        assigned_to = {}  # drone index -> field
        covered = set()

        # Step 2: full protection, highest threat first
        for field in threatened:
            need = need_of(field)
            if len(remaining) < need:
                continue  # cannot fully protect this field; do not partially cover it here
            ranked = sorted(remaining, key=lambda d: self._score(d, field))
            chosen = ranked[:need]
            for d in chosen:
                remaining.remove(d)
                assigned_to[id(d)] = field
            covered.add(field.id)

        # Step 3: leftovers partially cover at most one field (most threatened uncovered)
        if remaining:
            for field in threatened:
                if field.id in covered:
                    continue
                cap = need_of(field)
                ranked = sorted(remaining, key=lambda d: self._score(d, field))
                chosen = ranked[:min(cap, len(ranked))]
                for d in chosen:
                    remaining.remove(d)
                    assigned_to[id(d)] = field
                covered.add(field.id)
                break  # only one partially protected field

        # Apply assignments
        for d in drones:
            field = assigned_to.get(id(d))
            if field is not None and group_name(field) in group_ids:
                environment.assign_group(d, group_name(field))
            else:
                environment.assign_group(d, "idle")
```