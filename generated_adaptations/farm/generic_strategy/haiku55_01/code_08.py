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
    def _select_fields(items, capacity):
        """0/1 knapsack. items: list of (key, cost, value). Returns set of selected keys."""
        n = len(items)
        # dp[i][w] = best value using first i items with budget w
        dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            _, cost, value = items[i - 1]
            for w in range(capacity + 1):
                dp[i][w] = dp[i - 1][w]
                if cost <= w:
                    cand = dp[i - 1][w - cost] + value
                    if cand > dp[i][w] + 1e-12:
                        dp[i][w] = cand
        # Reconstruct
        selected = set()
        w = capacity
        for i in range(n, 0, -1):
            if dp[i][w] > dp[i - 1][w] + 1e-12:
                key, cost, _ = items[i - 1]
                selected.add(key)
                w -= cost
        return selected

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
        threat = {f.id: f.threat_level for f in fields}
        by_id = {f.id: f for f in fields}

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

        # Keep up to `need` reserved drones per field (protecting first, then closest).
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

        def assign_closest(field_id, k):
            nonlocal free
            field = by_id[field_id]
            free.sort(key=lambda d: self._dist(d, field))
            taken, free = free[:k], free[k:]
            for d in taken:
                assignment[id(d)] = field_id
            count[field_id] += len(taken)

        # Knapsack over fields that still need drones and can be completed.
        capacity = len(free)
        items = []
        for f in fields:
            deficit = need[f.id] - count[f.id]
            if 0 < deficit <= capacity:
                items.append((f.id, deficit, threat[f.id]))
        selected = self._select_fields(items, capacity)

        # Fill selected fields to full protection, highest threat first.
        for f in fields:
            if f.id in selected:
                deficit = need[f.id] - count[f.id]
                if deficit > 0:
                    assign_closest(f.id, deficit)

        # Leftover drones: reinforce the highest-threat field that is still incomplete,
        # otherwise the top field.
        while free:
            target = None
            for f in fields:
                if count[f.id] < need[f.id]:
                    target = f.id
                    break
            if target is None:
                target = fields[0].id
            assign_closest(target, 1)

        # Issue group assignments for every drone exactly once
        for d in drones:
            fid = assignment.get(id(d))
            if fid is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {fid}")