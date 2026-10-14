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

        # Drones already heading to / protecting a candidate field are reserved there
        reserved = {f.id: [] for f in fields}
        free = []
        for d in drones:
            if d.target_id in cand_ids and d.state in ("moving_to_field", "protecting"):
                reserved[d.target_id].append(d)
            else:
                free.append(d)

        assignment = {}  # id(drone) -> field id

        def take_closest(field, count_needed):
            nonlocal free
            free.sort(key=lambda d: self._dist(d, field))
            taken, free = free[:count_needed], free[count_needed:]
            for d in taken:
                assignment[id(d)] = field.id
            return taken

        # Pass 1: keep reserved drones (protecting first, then closest), release surplus
        count = {}
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

        # Pass 2: full coverage in threat order where the pool can reach it
        partial = []
        for f in fields:
            shortfall = need[f.id] - count[f.id]
            if shortfall <= 0:
                continue
            if shortfall <= len(free):
                take_closest(f, shortfall)
                count[f.id] += shortfall
            else:
                partial.append(f)

        # Pass 3: partial coverage for fields that could not be fully covered
        for f in partial:
            if not free:
                break
            shortfall = need[f.id] - count[f.id]
            if shortfall <= 0:
                continue
            taken = take_closest(f, min(shortfall, len(free)))
            count[f.id] += len(taken)

        # Leftover drones reinforce the highest-threat field
        if free:
            take_closest(fields[0], len(free))

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")