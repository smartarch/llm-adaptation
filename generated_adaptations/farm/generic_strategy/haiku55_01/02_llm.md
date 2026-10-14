## Strategy: threat-ordered full coverage with sticky assignments

1. **Candidate fields:** Consider only fields with `threat_level > 0`, sorted by threat (highest first, ties broken by id).
2. **Keep existing drones:** A drone already moving to or protecting a candidate field stays there, so it doesn't waste time flying again. Drones on each field are sorted with "protecting" drones first, then by distance, so the ones already in place are preferred.
3. **Pass 1, full coverage in threat order:** For each field, if the kept drones plus the free pool can reach `drones_for_full_protection`, assign exactly that many. Surplus kept drones are released to the free pool. The closest free drones fill any shortfall.
4. **Pass 2, partial coverage:** Fields that cannot be fully covered are handled in threat order. They keep their drones and receive the closest free drones. Partial protection still beats none, per the task description.
5. **No idle drones:** Any drones still free are sent to the highest-threat field as extra protection. If no field needs protection, they go to `idle`.

Each drone is assigned exactly once, and every assignment uses the exact group names from `group_ids`.

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

        # Candidate fields: threat > 0, highest threat first (deterministic tie-break by id)
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        if not fields:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        cand_ids = {f.id for f in fields}
        need = {f.id: max(1, int(f.drones_for_full_protection)) for f in fields}

        # Drones already heading to / protecting a candidate field are "reserved" there
        reserved = {f.id: [] for f in fields}
        free = []
        for d in drones:
            if d.target_id in cand_ids and d.state in ("moving_to_field", "protecting"):
                reserved[d.target_id].append(d)
            else:
                free.append(d)

        # Prefer drones already protecting, then closest ones (avoids unnecessary re-flying)
        for f in fields:
            reserved[f.id].sort(key=lambda d: (d.state != "protecting", self._dist(d, f)))

        assignment = {}  # id(drone) -> field

        def take_closest(field, count):
            nonlocal free
            free.sort(key=lambda d: self._dist(d, field))
            taken, free = free[:count], free[count:]
            for d in taken:
                assignment[id(d)] = field.id
            return taken

        # Pass 1: fully protect fields in threat order where possible
        partial = []
        for f in fields:
            n = need[f.id]
            kept = reserved[f.id]
            if len(kept) >= n:
                for d in kept[:n]:
                    assignment[id(d)] = f.id
                free.extend(kept[n:])  # surplus released to the pool
                continue
            shortfall = n - len(kept)
            if shortfall <= len(free):
                for d in kept:
                    assignment[id(d)] = f.id
                take_closest(f, shortfall)
            else:
                partial.append(f)

        # Pass 2: partially protect remaining fields in threat order
        for f in partial:
            for d in reserved[f.id]:
                assignment[id(d)] = f.id
            missing = need[f.id] - len(reserved[f.id])
            if missing > 0 and free:
                take_closest(f, min(missing, len(free)))

        # Leftover drones must not stay idle: reinforce the highest-threat field
        if free:
            for d in free:
                assignment[id(d)] = fields[0].id
            free = []

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")
```