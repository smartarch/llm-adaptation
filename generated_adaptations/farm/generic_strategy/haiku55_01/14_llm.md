## Analysis of the previous results

The threat-ordered full-coverage design has repeatedly measured 150.7, and the other variants were worse. The remaining weakness is in how that design treats drones that are already in place:

1. **Churn on fully protected fields.** When a field is fully protected, its drones are the ones keeping birds away. The current code sorts fields purely by threat, so a field that is fully protected can drop below a slightly higher-threat field after a small threat fluctuation. Its surplus drones are then released and sent elsewhere. Birds return as soon as protection lapses.
2. **Surplus drones released too early.** Any reserved drone beyond `need` goes straight into the free pool, even when there is a deficit elsewhere that could be filled from the free pool first. Releasing drones this early causes flights that are not required.

## Revised strategy: hysteresis and conservative release

I keep the threat-ordered full-coverage logic and change two things:

- **Priority for fields already fully protected.** Fields that are fully covered by their current drones are ordered first, then by threat. This avoids leaving a protected field because of a small threat change. Ties and the rest of the order still follow threat.
- **Surplus is a last resort.** Surplus drones stay on their field. They are only pulled away if a field cannot otherwise be completed. Drones that are truly unassigned (idle or in transit to a non-candidate field) are always used first.

The allocation then follows these steps:

1. Keep reserved drones on their fields, up to `need`. Store the extras as `spare`.
2. For each field in priority order, fill the shortfall from the free pool, and if that is not enough, from `spare`. Only full coverage is attempted this way.
3. Fields that still cannot reach full coverage take whatever is left, in priority order, as partial coverage.
4. Any remaining drones reinforce the highest-threat field.

I have not run the simulator, so this should be measured against the 150.7 baseline.

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
        if not fields:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        cand_ids = {f.id for f in fields}
        need = {f.id: max(1, int(f.drones_for_full_protection)) for f in fields}

        # Drones already heading to / protecting a candidate field
        reserved = {f.id: [] for f in fields}
        free = []
        for d in drones:
            if d.target_id in cand_ids and d.state in ("moving_to_field", "protecting"):
                reserved[d.target_id].append(d)
            else:
                free.append(d)

        assignment = {}  # id(drone) -> field id
        count = {}
        spare = []       # reserved drones beyond need: used only as a last resort

        for f in fields:
            kept = sorted(
                reserved[f.id],
                key=lambda d: (d.state != "protecting", self._dist(d, f)),
            )
            keep, extra = kept[:need[f.id]], kept[need[f.id]:]
            for d in keep:
                assignment[id(d)] = f.id
            count[f.id] = len(keep)
            spare.extend(extra)

        # Hysteresis: fields already fully protected come first, then by threat.
        fields.sort(key=lambda f: (
            0 if count[f.id] >= need[f.id] else 1,
            -f.threat_level,
            str(f.id),
        ))

        def take_closest(field, k):
            """Take k drones for field: free pool first (closest), then spare."""
            nonlocal free, spare
            taken = []
            free.sort(key=lambda d: self._dist(d, field))
            n_free = min(k, len(free))
            taken.extend(free[:n_free])
            free = free[n_free:]
            remaining = k - n_free
            if remaining > 0:
                spare.sort(key=lambda d: self._dist(d, field))
                taken.extend(spare[:remaining])
                spare = spare[remaining:]
            for d in taken:
                assignment[id(d)] = field.id
            count[field.id] += len(taken)
            return len(taken)

        # Pass 1: full coverage in priority order, using free drones first
        partial = []
        for f in fields:
            shortfall = need[f.id] - count[f.id]
            if shortfall <= 0:
                continue
            if shortfall <= len(free) + len(spare):
                take_closest(f, shortfall)
            else:
                partial.append(f)

        # Pass 2: partial coverage for fields that could not be completed
        for f in partial:
            if not free and not spare:
                break
            shortfall = need[f.id] - count[f.id]
            if shortfall <= 0:
                continue
            take_closest(f, min(shortfall, len(free) + len(spare)))

        # Remaining drones (free or spare) reinforce the highest-priority field
        leftovers = free + spare
        if leftovers:
            top = fields[0]
            free = []
            spare = []
            for d in leftovers:
                assignment[id(d)] = top.id
            count[top.id] += len(leftovers)

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")
```