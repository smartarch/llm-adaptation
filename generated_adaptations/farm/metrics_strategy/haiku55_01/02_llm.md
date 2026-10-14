## Strategy: Threat-Prioritized Greedy Allocation with Sticky Drones

**Goal:** Fully protect the most threatened fields first, use only as many drones as each field needs, and avoid unnecessary drone movement.

**Approach:**

1. **Select active fields.** Keep only fields with `threat_level > 0` whose protection group is in `group_ids`. Sort them by threat (highest first), with the field id as a tie-breaker so the order is deterministic.
2. **Full-protection pass (priority order).** For each field, if enough unassigned drones remain to reach `drones_for_full_protection`, assign exactly that many. Drones are ranked by:
   - whether they already target this field (to avoid unnecessary reassignments and keep existing protection in place), then
   - distance from the drone to the field center (closest first).
   
   A field that cannot be fully protected with the remaining drones is skipped, so the drones can go to lower-priority fields that can be fully covered.
3. **Partial pass for leftovers.** Any drones still unassigned go to the remaining fields in priority order, filling each up to its requirement with the same ranking. Partial protection is still better than none. Because every field that could be fully protected was already handled, these leftovers only ever reach fields that cannot be fully covered.
4. **Idle remainder.** Drones that are still unassigned after both passes (no field needs them) are placed in the `"idle"` group, so no drone is ever left unassigned.

Every component receives exactly one `assign_group` call. The code only uses group names that appear in `group_ids`, and the distance and threat values come from the read-only environment and component attributes.

```py
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Threat-prioritized greedy allocation with sticky drones:
    1. Fields with threat > 0 are processed from highest to lowest threat.
    2. Each field is fully protected with exactly `drones_for_full_protection`
       drones if enough unassigned drones remain. Drones already heading to or
       protecting that field are preferred, then the closest drones are used.
    3. Fields that cannot be fully covered are skipped in the full pass; leftover
       drones are used for partial protection in priority order.
    4. Any drones still unused are sent to the "idle" group.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone, field):
        cx, cy = self._field_center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        comps = list(components)

        # 1. Active fields sorted by threat (highest first), deterministic tie-break by id.
        fields = [
            f for f in environment.fields
            if f.threat_level > 0 and f"protecting {f.id}" in valid_groups
        ]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        assigned = {}          # component index -> field id
        count = {f.id: 0 for f in fields}
        unassigned = set(range(len(comps)))

        def rank(idx, field):
            drone = comps[idx]
            # Prefer drones already targeting this field (no unnecessary flights),
            # then the closest ones.
            return (drone.target_id != field.id, self._distance(drone, field))

        def fill(field, needed):
            """Assign up to `needed` unassigned drones to `field`, best-ranked first."""
            if needed <= 0 or not unassigned:
                return 0
            ranked = sorted(unassigned, key=lambda idx: rank(idx, field))
            chosen = ranked[:needed]
            for idx in chosen:
                assigned[idx] = field.id
                unassigned.discard(idx)
            count[field.id] += len(chosen)
            return len(chosen)

        # 2. Full-protection pass in priority order.
        full_need = {f.id: max(0, int(f.drones_for_full_protection)) for f in fields}
        for field in fields:
            need = full_need[field.id]
            if need == 0:
                continue
            if len(unassigned) >= need:
                fill(field, need)

        # 3. Partial pass: leftover drones go to the highest-priority fields
        #    that are still short of full protection.
        for field in fields:
            if not unassigned:
                break
            remaining = full_need[field.id] - count[field.id]
            if remaining > 0:
                fill(field, remaining)

        # 4. Everything else is idle.
        for idx, drone in enumerate(comps):
            if idx in assigned:
                environment.assign_group(drone, f"protecting {assigned[idx]}")
            else:
                environment.assign_group(drone, "idle")
```