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

    @staticmethod
    def _value(threat, need, count):
        # Partial coverage earns credit proportional to coverage;
        # full protection earns an extra bonus (birds only flee when fully protected).
        covered = min(count, need) / need
        full = 1.0 if count >= need else 0.0
        return threat * (0.5 * covered + 0.5 * full)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)

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
        count = {}

        # Keep up to `need` reserved drones per field (protecting ones first, then closest);
        # release surplus to the free pool.
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

        # Greedy allocation: each free drone goes to the field with the largest marginal gain
        while free:
            best_field = None
            best_gain = 0.0
            for f in fields:  # threat order, so ties favour higher threat
                n = need[f.id]
                c = count[f.id]
                gain = (self._value(f.threat_level, n, c + 1)
                        - self._value(f.threat_level, n, c))
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_field = f

            if best_field is None:
                # Every field is fully covered: reinforce the highest-threat field
                best_field = fields[0]

            free.sort(key=lambda d: self._dist(d, best_field))
            drone = free.pop(0)
            assignment[id(drone)] = best_field.id
            count[best_field.id] += 1

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")