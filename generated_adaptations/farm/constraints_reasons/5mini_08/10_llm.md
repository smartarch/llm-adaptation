Reasoning and strategy

What I changed and why

- Previous attempts sometimes prioritized preserving long-running assignments over using the absolute closest drones for the most threatened field. The requirements explicitly say: "The most threatened field should be always fully protected" and "The drones protecting the most threatened field should be the closest ones." To honor that more strictly, this version forces the top (highest threat_level) field to be protected by the closest available drones (based on travel time), even if that means moving drones that had been assigned elsewhere. This reduces the time until the top field is actually fully protected.

- For other fields we keep the "fastest-to-arrive" selection idea: for a field requiring k drones, choose the k available drones with the smallest estimated arrival times (arrival = distance / speed, with speed = 2). This minimizes the time until full protection (the time determined by the slowest of the selected drones).

- Field selection beyond the top field is greedy by an urgency score that balances current threat, short-term trend (if available), drones required, and time-to-full (the max arrival among the chosen k). The score favors high-threat, rising fields that can be fully protected quickly with few drones.

- Stability is respected but secondary to protecting the top field: when choosing among drones with similar arrival times we prefer drones already assigned to the target field or with short prev_steps to avoid breaking long-lived assignments unnecessarily — but only as a tie-breaker. This keeps churn reasonable while ensuring we get the closest drones to the top field.

- We always avoid overprotection (never assign more than drones_for_full_protection). We aim to use at least half of the drones for protection when possible.

Implementation notes

- We track per-drone previous group and consecutive steps to guide tie-breaking for stability.
- For each field, arrival_time(dm, field) = 0 if the drone is already protecting or moving to that field (or if it was previously assigned to that group by us); otherwise it's Euclidean distance to field center divided by speed (2).
- For the top field we strictly pick k drones with smallest arrival_time (tie-breaking by prev_steps).
- For other fields we pick k smallest arrival_time among currently available drones; compute time_to_full = max of those arrival times; then urgency score = (threat + trend_weight * positive_trend) / ((time_to_full + eps) * k). Greedily pick highest-scoring fields until we reach at least half the drones or no full-protection options remain.

Code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict, deque
from typing import Any

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # drone id -> (last_group, consecutive_steps)
        self._prev = {}
        # field id -> deque of recent threat_level readings for simple trend estimation
        self._field_history = defaultdict(lambda: deque(maxlen=6))

    def _center(self, field: Any):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total_drones = len(drones)

        # update field history and gather fields with positive threat
        fields_all = list(environment.fields)
        current_ids = {f.id for f in fields_all}
        # prune histories for removed fields
        for fid in list(self._field_history.keys()):
            if fid not in current_ids:
                del self._field_history[fid]
        for f in fields_all:
            self._field_history[f.id].append(getattr(f, "threat_level", 0.0))

        fields = [f for f in fields_all if getattr(f, "threat_level", 0.0) > 0.0]

        # helper group id
        def protecting_gid(fid):
            return f"protecting {fid}"

        # prepare centers
        centers = {f.id: self._center(f) for f in fields}

        # build drone metadata
        drone_meta = []
        for d in drones:
            did = id(d)
            prev_group, prev_steps = self._prev.get(did, (None, 0))
            loc = getattr(d, "location", None)
            lx = getattr(loc, "x", 0.0) if loc is not None else 0.0
            ly = getattr(loc, "y", 0.0) if loc is not None else 0.0
            drone_meta.append({
                "obj": d,
                "id": did,
                "x": lx,
                "y": ly,
                "state": getattr(d, "state", None),
                "target_id": getattr(d, "target_id", None),
                "prev_group": prev_group,
                "prev_steps": prev_steps,
            })

        # arrival time estimate (speed = 2). If drone already assigned/moving to that field treat as immediate.
        def arrival_time(dm, field):
            gid = protecting_gid(field.id)
            # if we previously assigned it to that protecting group, treat as immediate (stability)
            if dm["prev_group"] == gid:
                return 0.0
            # if drone currently protecting or moving to that target, treat as immediate
            if dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == field.id:
                return 0.0
            cx, cy = centers[field.id]
            return self._dist(dm["x"], dm["y"], cx, cy) / 2.0

        # helper: choose best k drones (smallest arrival_time). Tie-breaker prefers drones already assigned to that group
        # or with smaller prev_steps to reduce churn.
        def pick_k_for_field(field, k, available_drones):
            gid = protecting_gid(field.id)
            cand = list(available_drones)
            # sort by arrival_time, then prefer those whose prev_group == gid (stability), then fewer prev_steps
            def key(dm):
                # arrival
                at = arrival_time(dm, field)
                # prefer current/prev assign to that gid
                same_group = 0 if dm["prev_group"] == gid or (dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == field.id) else 1
                return (at, same_group, dm["prev_steps"])
            cand.sort(key=key)
            selected = cand[:k]
            if not selected:
                time_to_full = float("inf")
            else:
                time_to_full = max(arrival_time(dm, field) for dm in selected)
            return selected, time_to_full

        # final assignment mapping drone id -> group
        final_assign = {}

        # if no fields threatened: idle all (explicit re-assignment)
        if not fields:
            for dm in drone_meta:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(dm["obj"], assigned)
                last_group, last_steps = self._prev.get(dm["id"], (None, 0))
                if last_group == assigned:
                    self._prev[dm["id"]] = (assigned, last_steps + 1)
                else:
                    self._prev[dm["id"]] = (assigned, 1)
            return

        # determine the top (most threatened) field and enforce it is protected by the closest drones
        fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = fields[0]
        top_gid = protecting_gid(top_field.id)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        # build list of available drone meta
        def available_list():
            return [dm for dm in drone_meta if dm["id"] not in final_assign]

        if required_top > 0 and top_gid in group_ids:
            avail = available_list()
            # For top field, strict closeness rule: pick k drones with smallest arrival_time (tie-breaker prev_steps)
            avail.sort(key=lambda dm: (arrival_time(dm, top_field), dm["prev_steps"]))
            chosen_top = avail[:required_top]
            for dm in chosen_top:
                final_assign[dm["id"]] = top_gid

        # target to use at least half drones for protection
        min_protect = math.ceil(total_drones / 2.0)
        protected_now = sum(1 for g in final_assign.values() if g != "idle")

        # prepare remaining fields for greedy selection
        remaining_fields = [f for f in fields if f.id != top_field.id]

        # compute simple trend (current - avg(previous)) to boost rising fields
        field_trend = {}
        for f in remaining_fields:
            hist = list(self._field_history.get(f.id, []))
            if len(hist) <= 1:
                field_trend[f.id] = 0.0
            else:
                curr = hist[-1]
                prev_avg = sum(hist[:-1]) / max(1, len(hist) - 1)
                field_trend[f.id] = curr - prev_avg

        # greedy selection: compute urgency score for each remaining field and allocate the best one iteratively
        # score = (threat + trend_weight * positive_trend) / ((time_to_full + eps) * drones_required)
        TREND_WEIGHT = 2.0
        EPS = 1e-6

        while protected_now < min_protect:
            best_score = -1.0
            best_choice = None  # tuple (field, selected_list, time_to_full)
            avail = available_list()
            if not avail:
                break
            for f in remaining_fields:
                gid = protecting_gid(f.id)
                if gid not in group_ids:
                    continue
                k = int(getattr(f, "drones_for_full_protection", 0))
                if k <= 0:
                    continue
                if len(avail) < k:
                    continue
                # pick k best among available
                sel, t_full = pick_k_for_field(f, k, avail)
                if not sel or t_full == float("inf"):
                    continue
                threat = getattr(f, "threat_level", 0.0)
                trend = field_trend.get(f.id, 0.0)
                benefit = threat + TREND_WEIGHT * max(trend, 0.0)
                # per-drone normalized urgency (higher is better)
                score = benefit / ((t_full + EPS) * max(1, k))
                # tie-breaker: higher raw threat
                if score > best_score:
                    best_score = score
                    best_choice = (f, sel, t_full)
            if best_choice is None:
                break
            f_sel, sel_drones, _ = best_choice
            gid_sel = protecting_gid(f_sel.id)
            for dm in sel_drones:
                final_assign[dm["id"]] = gid_sel
            protected_now = sum(1 for g in final_assign.values() if g != "idle")
            # remove field from remaining
            remaining_fields = [f for f in remaining_fields if f.id != f_sel.id]

        # If still under min_protect, try to fill with cheapest (smallest k) fields by threat to reach half
        if protected_now < min_protect:
            # sort remaining fields by small drones_for_full_protection then by threat
            cheap_sorted = sorted([f for f in remaining_fields if protecting_gid(f.id) in group_ids], key=lambda f: (int(getattr(f, "drones_for_full_protection", 0)), -getattr(f, "threat_level", 0.0)))
            for f in cheap_sorted:
                if protected_now >= min_protect:
                    break
                k = int(getattr(f, "drones_for_full_protection", 0))
                if k <= 0:
                    continue
                avail = available_list()
                if len(avail) < k:
                    continue
                sel, _ = pick_k_for_field(f, k, avail)
                for dm in sel:
                    final_assign[dm["id"]] = protecting_gid(f.id)
                protected_now = sum(1 for g in final_assign.values() if g != "idle")

        # assign remaining drones to idle explicitly
        for dm in drone_meta:
            if dm["id"] not in final_assign:
                final_assign[dm["id"]] = "idle"

        # apply assignments and update prev tracking
        for dm in drone_meta:
            obj = dm["obj"]
            did = dm["id"]
            assigned = final_assign.get(did, "idle")
            if assigned not in group_ids:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            environment.assign_group(obj, assigned)
            last_group, last_steps = self._prev.get(did, (None, 0))
            if last_group == assigned:
                self._prev[did] = (assigned, last_steps + 1)
            else:
                self._prev[did] = (assigned, 1)
```