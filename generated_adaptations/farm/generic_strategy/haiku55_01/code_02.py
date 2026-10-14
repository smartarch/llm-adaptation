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