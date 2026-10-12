from typing import Dict, Any, List, Tuple
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: drone_key -> {"group": group_id, "since": step}
        self._history: Dict[Any, Dict[str, Any]] = {}

    def _drone_key(self, component):
        return getattr(component, "id", id(component))

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, loc, fx, fy):
        dx = getattr(loc, "x", 0.0) - fx
        dy = getattr(loc, "y", 0.0) - fy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Seed history for drones
        drone_infos: Dict[Any, Dict[str, Any]] = {}
        for comp in components:
            key = self._drone_key(comp)
            if key not in self._history:
                # infer group from observed state
                state = getattr(comp, "state", None)
                target = getattr(comp, "target_id", None)
                if state == "protecting" and target is not None:
                    inferred = f"protecting {target}"
                else:
                    inferred = "idle"
                self._history[key] = {"group": inferred, "since": step}
            drone_infos[key] = {
                "component": comp,
                "last_group": self._history[key]["group"],
                "since": self._history[key]["since"],
            }

        total_drones = len(components)
        min_protectors_target = math.ceil(total_drones / 2)

        # Gather threatened fields
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # no threatened fields -> idle all
            for comp in components:
                environment.assign_group(comp, "idle")
                key = self._drone_key(comp)
                if self._history.get(key, {}).get("group") != "idle":
                    self._history[key] = {"group": "idle", "since": step}
            return

        # Identify top field (highest threat) - must be included
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = fields_sorted[0]
        top_w = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
        # Ensure top_w doesn't exceed total_drones gracefully
        if top_w > total_drones:
            top_w = total_drones

        # Prepare knapsack items for remaining fields
        remaining_fields = fields_sorted[1:]
        items = []
        for i, f in enumerate(remaining_fields):
            w = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            v = float(getattr(f, "threat_level", 0.0))
            # skip fields needing zero drones
            if w <= 0 or v <= 0.0:
                continue
            items.append((i, f, w, v))

        capacity = total_drones - top_w
        selected_fields = [top_field]  # must include top

        # Solve 0-1 knapsack (small n) to choose subset of remaining fields maximizing total threat
        if capacity > 0 and items:
            # dp[c] = total value achievable with capacity c, track choices
            n = len(items)
            # dp table: (n+1) x (capacity+1)
            dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]
            take = [[False] * (capacity + 1) for _ in range(n + 1)]
            for i in range(1, n + 1):
                _, f, w, v = items[i - 1]
                for c in range(capacity + 1):
                    # don't take
                    best = dp[i - 1][c]
                    take_it = False
                    if w <= c:
                        val_if_taken = dp[i - 1][c - w] + v
                        if val_if_taken > best:
                            best = val_if_taken
                            take_it = True
                    dp[i][c] = best
                    take[i][c] = take_it
            # reconstruct chosen
            c = capacity
            chosen_indices = []
            for i in range(n, 0, -1):
                if take[i][c]:
                    chosen_indices.append(i - 1)
                    _, _, w, _ = items[i - 1]
                    c -= w
            for idx in reversed(chosen_indices):
                _, f, _, _ = items[idx]
                selected_fields.append(f)

        # Now, allocate drones to exactly these selected_fields (each full protection)
        allocation: Dict[str, List[Any]] = {}
        assigned_keys = set()

        # Helper to generate candidate scores for a field
        def candidates_for_field(field):
            fx, fy = self._field_center(field)
            desired_group = f"protecting {field.id}"
            cand = []
            for key, info in drone_infos.items():
                if key in assigned_keys:
                    continue
                comp = info["component"]
                dist = self._distance(comp.location, fx, fy)
                last_group = info["last_group"]
                since_steps = max(0, step - info["since"])
                # small penalty for reassigning long-stable drones
                penalty = 0.02 * float(since_steps)
                # cap penalty so it doesn't dominate
                if penalty > 3.0:
                    penalty = 3.0
                # bonus if already moving to this field
                moving_bonus = 0.0
                if getattr(comp, "state", None) == "moving_to_field" and getattr(comp, "target_id", None) == field.id:
                    moving_bonus = -0.3
                # prefer drones already protecting this exact field (set penalty to negative tiny)
                protecting_bonus = 0.0
                if last_group == desired_group:
                    protecting_bonus = -0.5  # strongly favor those already protecting
                score = dist + penalty + moving_bonus + protecting_bonus
                cand.append((key, score, dist, since_steps, last_group))
            # sort by score ascending
            cand.sort(key=lambda x: (x[1], x[2], -x[3]))
            return cand

        # Allocate for each selected field: first reserve drones already protecting that field
        for field in selected_fields:
            group_name = f"protecting {field.id}"
            need = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            if need <= 0:
                allocation[group_name] = []
                continue
            # Prefill with drones already protecting this group (and not yet assigned)
            already = []
            for key, info in drone_infos.items():
                if key in assigned_keys:
                    continue
                if info["last_group"] == group_name:
                    already.append((key, info["since"]))
            # sort already by longest-serving (earliest since)
            already_sorted = sorted(already, key=lambda x: x[1])
            chosen = []
            for k, _ in already_sorted:
                if len(chosen) >= need:
                    break
                chosen.append(k)
                assigned_keys.add(k)
            # Fill remaining from candidates
            if len(chosen) < need:
                cands = candidates_for_field(field)
                for k, _, _, _, _ in cands:
                    if k in assigned_keys:
                        continue
                    chosen.append(k)
                    assigned_keys.add(k)
                    if len(chosen) >= need:
                        break
            allocation[group_name] = chosen

        # If for some reason we couldn't allocate enough drones to a selected field (e.g. top_w > total_drones),
        # we've already assigned as many as possible. No overprotection allowed.
        # Remaining drones -> try to allocate to other unselected fields if there's spare and it doesn't break stability:
        remaining_keys = [k for k in drone_infos.keys() if k not in assigned_keys]
        # compute how many protectors we have
        current_protected = sum(len(v) for v in allocation.values())
        # If we have fewer than half protecting, try to add additional full protections from unselected fields greedily (by benefit/weight)
        if current_protected < min_protectors_target:
            # candidate unselected fields
            unselected = [f for f in fields_sorted if f not in selected_fields]
            # sort by benefit per drone
            unselected_sorted = sorted(unselected, key=lambda f: (getattr(f, "threat_level", 0) / max(1, getattr(f, "drones_for_full_protection", 1))), reverse=True)
            for f in unselected_sorted:
                need = max(0, int(getattr(f, "drones_for_full_protection", 0)))
                if need <= 0:
                    continue
                remaining = total_drones - sum(len(v) for v in allocation.values())
                if need > remaining:
                    continue
                # allocate
                cands = candidates_for_field(f)
                picks = []
                for k, _, _, _, _ in cands:
                    if k in assigned_keys:
                        continue
                    picks.append(k)
                    assigned_keys.add(k)
                    if len(picks) >= need:
                        break
                if picks:
                    allocation[f"protecting {f.id}"] = picks
                current_protected = sum(len(v) for v in allocation.values())
                if current_protected >= min_protectors_target:
                    break

        # Finally, any drone not allocated -> idle
        final_assignments: Dict[Any, str] = {}
        for key in drone_infos:
            assigned = None
            for g, keys in allocation.items():
                if key in keys:
                    assigned = g
                    break
            if assigned is None:
                assigned = "idle"
            final_assignments[key] = assigned

        # Commit assignments and update history
        for key, info in drone_infos.items():
            comp = info["component"]
            group = final_assignments[key]
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)
            prev = self._history.get(key)
            if prev is None or prev.get("group") != group:
                self._history[key] = {"group": group, "since": step}
            # else keep the previous 'since' for continuity