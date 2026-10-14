import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    BAND_WIDTH = 0.1  # threat levels within the same band are treated as ties

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

        # Priority: fully protected first, then threat band (higher first),
        # then drones already in place, then id for determinism.
        def priority(f):
            band = round(f.threat_level / self.BAND_WIDTH)
            return (
                0 if count[f.id] >= need[f.id] else 1,
                -band,
                0 if count[f.id] > 0 else 1,
                str(f.id),
            )

        fields.sort(key=priority)

        def take_closest(field, k):
            """Take k drones for field: free pool first (closest), then spare."""
            nonlocal free, spare
            free.sort(key=lambda d: self._dist(d, field))
            n_free = min(k, len(free))
            taken = free[:n_free]
            free = free[n_free:]
            remaining = k - n_free
            if remaining > 0:
                spare.sort(key=lambda d: self._dist(d, field))
                taken += spare[:remaining]
                spare = spare[remaining:]
            for d in taken:
                assignment[id(d)] = field.id
            count[field.id] += len(taken)

        # Pass 1: full coverage in priority order
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

        # Leftovers go to the highest-priority field that is still incomplete.
        # Only when every field is complete do they reinforce the top field.
        leftovers = free + spare
        free = []
        spare = []
        for d in leftovers:
            target = None
            for f in fields:
                if count[f.id] < need[f.id]:
                    target = f
                    break
            if target is None:
                target = fields[0]
            assignment[id(d)] = target.id
            count[target.id] += 1

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")