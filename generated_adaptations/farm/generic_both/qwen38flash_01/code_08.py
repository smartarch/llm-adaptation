import math
from typing import List, Dict, Set, Tuple, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Knapsack-optimized protection strategy with hysteresis:
    - Selects optimal subset of fields to fully protect via DP knapsack.
    - Hysteresis prevents oscillation between similar plans.
    - Proximity-aware drone-to-field assignment minimizes transit waste.
    - Never assigns drones to non-selected fields (partial = useless).
    - No idle drones when active fields exist.
    """

    # Hysteresis margin: only switch plans if improvement > this fraction
    HYSTERESIS_MARGIN = 0.20
    # Transit penalty: distance units that count as equivalent to "staying put"
    STAY_BONUS = 5.0

    def _get_field_group(self, field, group_ids: List[str]) -> str:
        fid_str = str(field.id)
        for gid in group_ids:
            if gid == "idle":
                continue
            if gid == fid_str:
                return gid
            if gid == f"protecting_{fid_str}":
                return gid
            if gid == f"protect_{fid_str}":
                return gid
            if gid == f"field_{fid_str}":
                return gid
            if fid_str in gid and "idle" not in gid.lower():
                return gid
        return "idle"

    @staticmethod
    def _dist_to_field(drone, field) -> float:
        cx = (field.left + field.right) * 0.5
        cy = (field.top + field.bottom) * 0.5
        dx = drone.location.x - cx
        dy = drone.location.y - cy
        return math.hypot(dx, dy)

    def _solve_knapsack(self, fields: list, budget: int) -> Tuple[List[int], float]:
        """
        DP knapsack: select subset of fields maximizing total threat_level
        subject to sum(drones_for_full_protection) <= budget.
        Returns (list_of_field_indices, total_threat_value).
        """
        n = len(fields)
        if n == 0:
            return [], 0.0

        # Separate zero-cost fields (always included)
        zero_cost = []
        items = []  # (index, cost, value)
        for i, f in enumerate(fields):
            cost = f.drones_for_full_protection
            if cost <= 0:
                zero_cost.append(i)
            else:
                items.append((i, cost, f.threat_level))

        base_value = sum(fields[i].threat_level for i in zero_cost)

        m = len(items)
        if m == 0:
            return zero_cost, base_value

        # Cap budget for DP array size
        max_b = min(budget, sum(c for _, c, _ in items))

        # dp[w] = (max_value, chosen_indices_set)
        # Using value maximization with reconstruction
        NEG = -1.0
        dp = [NEG] * (max_b + 1)
        dp[0] = base_value
        choice = [[False] * (m + 1) for _ in range(max_b + 1)]

        for j, (fi, cost, val) in enumerate(items):
            for w in range(max_b, cost - 1, -1):
                if dp[w - cost] > NEG:
                    new_val = dp[w - cost] + val
                    if new_val > dp[w]:
                        dp[w] = new_val
                        # Copy choices from w-cost and add j
                        for k in range(m):
                            choice[w][k] = choice[w - cost][k]
                        choice[w][j] = True

        # Find best
        best_val = NEG
        best_w = 0
        for w in range(max_b + 1):
            if dp[w] > best_val:
                best_val = dp[w]
                best_w = w

        selected = list(zero_cost)
        for j in range(m):
            if choice[best_w][j]:
                selected.append(items[j][0])

        return selected, best_val

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)

        # --- Active fields ---
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        if not active_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort by threat descending (for tie-breaking in assignment order)
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # --- Compute optimal protection plan ---
        selected_indices, plan_value = self._solve_knapsack(active_fields, total_drones)
        selected_fields = [active_fields[i] for i in selected_indices]
        # Re-sort selected fields by threat descending for assignment priority
        selected_fields.sort(key=lambda f: f.threat_level, reverse=True)
        selected_set = {str(f.id) for f in selected_fields}

        # --- Hysteresis: keep previous plan if close enough ---
        prev_plan = getattr(self, '_prev_plan', None)
        prev_plan_value = getattr(self, '_prev_plan_value', 0.0)

        if prev_plan is not None:
            prev_set = set(prev_plan)
            # Check if new plan is significantly better
            if plan_value < prev_plan_value * (1.0 + self.HYSTERESIS_MARGIN):
                # Keep previous plan if it's still feasible
                # (all fields in prev_plan still exist and have threat > 0)
                prev_feasible = all(
                    any(str(f.id) == pid and f.threat_level > 0 for f in environment.fields)
                    for pid in prev_set
                )
                if prev_feasible:
                    # Check total cost of prev plan fits in budget
                    prev_cost = sum(
                        f.drones_for_full_protection
                        for f in environment.fields
                        if str(f.id) in prev_set and f.threat_level > 0
                    )
                    if prev_cost <= total_drones:
                        selected_fields = [
                            f for f in environment.fields
                            if str(f.id) in prev_set and f.threat_level > 0
                        ]
                        selected_fields.sort(key=lambda f: f.threat_level, reverse=True)
                        selected_set = prev_set
                        plan_value = prev_plan_value

        self._prev_plan = list(selected_set)
        self._prev_plan_value = plan_value

        field_need = {str(f.id): f.drones_for_full_protection for f in selected_fields}
        field_by_id = {str(f.id): f for f in selected_fields}

        # --- Determine current assignments ---
        drone_current: Dict[int, Optional[str]] = {}
        for d in components:
            tgt = getattr(d, 'target_id', None)
            if tgt is not None and str(tgt) in selected_set:
                drone_current[id(d)] = str(tgt)
            else:
                drone_current[id(d)] = None

        # --- Phase 1: Keep drones on selected fields (up to capacity) ---
        assigned: Dict[int, str] = {}  # drone_id -> field_id
        field_drones: Dict[str, List[int]] = {str(f.id): [] for f in selected_fields}

        for f in selected_fields:
            fid = str(f.id)
            cap = field_need[fid]
            candidates = [(id(d), d) for d in components if drone_current.get(id(d)) == fid]
            candidates.sort(key=lambda x: self._dist_to_field(x[1], f))
            for d_id, _ in candidates:
                if d_id in assigned:
                    continue
                if len(field_drones[fid]) < cap:
                    field_drones[fid].append(d_id)
                    assigned[d_id] = fid

        # --- Phase 2: Fill remaining slots with closest unassigned drones ---
        unassigned = [d for d in components if id(d) not in assigned]

        for f in selected_fields:
            fid = str(f.id)
            remaining = field_need[fid] - len(field_drones[fid])
            if remaining <= 0:
                continue
            # Sort by effective distance: raw distance minus stay bonus if already nearby
            def eff_dist(d, fld=f):
                raw = self._dist_to_field(d, fld)
                # If drone was previously on this exact field, huge bonus to stay
                if drone_current.get(id(d)) == fid:
                    raw -= 1000.0
                elif drone_current.get(id(d)) is not None:
                    # Was on another field; penalize moving
                    raw += self.STAY_BONUS
                return raw

            candidates = sorted(unassigned, key=eff_dist)
            for d in candidates:
                if remaining <= 0:
                    break
                if id(d) in assigned:
                    continue
                field_drones[fid].append(id(d))
                assigned[id(d)] = fid
                remaining -= 1

        # --- Phase 3: Pull from non-selected fields if still deficits ---
        # (Only possible if Phase 2 pool was exhausted, meaning we have fewer
        #  drones than needed for the plan — unlikely but handle gracefully)
        for f in selected_fields:
            fid = str(f.id)
            deficit = field_need[fid] - len(field_drones[fid])
            if deficit <= 0:
                continue
            # Find drones on non-selected fields
            pullable = [d for d in components if id(d) not in assigned]
            if not pullable:
                break
            pullable.sort(key=lambda d: self._dist_to_field(d, f))
            for d in pullable:
                if deficit <= 0:
                    break
                field_drones[fid].append(id(d))
                assigned[id(d)] = fid
                deficit -= 1

        # --- Phase 4: Surplus drones → highest-threat selected field ---
        surplus = [d for d in components if id(d) not in assigned]
        if surplus and selected_fields:
            # Distribute surplus round-robin among selected fields (as reserves)
            rr_idx = 0
            for d in surplus:
                f = selected_fields[rr_idx % len(selected_fields)]
                fid = str(f.id)
                field_drones[fid].append(id(d))
                assigned[id(d)] = fid
                rr_idx += 1

        # --- Phase 5: Safety — ensure no drone is left truly idle ---
        for d in components:
            if id(d) not in assigned:
                if selected_fields:
                    assigned[id(d)] = str(selected_fields[0].id)
                else:
                    assigned[id(d)] = None

        # --- Final assignment ---
        for d in components:
            d_id = id(d)
            fid = assigned.get(d_id)
            if fid is not None and fid in field_by_id:
                gname = self._get_field_group(field_by_id[fid], group_ids)
                environment.assign_group(d, gname)
            else:
                environment.assign_group(d, "idle")