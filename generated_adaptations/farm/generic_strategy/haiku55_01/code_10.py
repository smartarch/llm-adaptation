import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    TRAVEL_WEIGHT = 0.02   # score penalty per unit of flight time
    STICKY_BONUS = 0.15    # bonus for keeping a drone on its current field
    DRONE_SPEED = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _travel_time(self, drone, field):
        cx, cy = self._center(field)
        dist = math.hypot(drone.location.x - cx, drone.location.y - cy)
        return dist / self.DRONE_SPEED

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)

        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        if not fields:
            for d in drones:
                environment.assign_group(d, "idle")
            return

        cand_ids = {f.id for f in fields}
        by_id = {f.id: f for f in fields}
        need = {f.id: max(1, int(f.drones_for_full_protection)) for f in fields}
        capacity = dict(need)

        # Current assignment of each drone (only if it targets a candidate field)
        current = {}
        for d in drones:
            if d.target_id in cand_ids and d.state in ("moving_to_field", "protecting"):
                current[id(d)] = d.target_id

        assignment = {}  # id(drone) -> field id

        # Step 1: keep drones already on a field, up to that field's capacity.
        # Protecting drones are kept before ones still in transit.
        on_field = {f.id: [] for f in fields}
        for d in drones:
            if id(d) in current:
                on_field[current[id(d)]].append(d)
        for f in fields:
            kept = sorted(
                on_field[f.id],
                key=lambda d: (d.state != "protecting", self._travel_time(d, f)),
            )
            for d in kept[:capacity[f.id]]:
                assignment[id(d)] = f.id
                capacity[f.id] -= 1

        free = [d for d in drones if id(d) not in assignment]

        # Step 2: score every (free drone, field with remaining capacity) pair.
        # Value = share of the field's threat one slot protects, minus flight cost.
        pairs = []
        for d in free:
            for f in fields:
                if capacity[f.id] <= 0:
                    continue
                value = f.threat_level / need[f.id]
                score = value - self.TRAVEL_WEIGHT * self._travel_time(d, f)
                if current.get(id(d)) == f.id:
                    score += self.STICKY_BONUS
                pairs.append((score, id(d), d, f.id))
        pairs.sort(key=lambda p: -p[0])

        # Step 3: greedy matching, best pair first.
        used = set()
        for score, did, d, fid in pairs:
            if did in used or capacity[fid] <= 0:
                continue
            assignment[did] = fid
            capacity[fid] -= 1
            used.add(did)

        # Step 4: leftover drones go to the highest-threat incomplete field,
        # otherwise to the top field.
        leftover = [d for d in free if id(d) not in assignment]
        for d in leftover:
            target = None
            for f in fields:
                if capacity[f.id] > 0:
                    target = f.id
                    break
            if target is None:
                target = fields[0].id
            assignment[id(d)] = target
            capacity[target] -= 1

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")