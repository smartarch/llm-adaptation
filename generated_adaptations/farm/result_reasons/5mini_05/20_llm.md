Reasoning and strategy

Improvements over the last working version (avg damage 101.3):

- Introduce a short hold-time for recently assigned protecting drones (default 3 steps). Drones that were assigned to protect a field recently should stay there for at least hold_time steps unless overriding to fulfill the strict primary protection requirement. This reduces excessive churn and keeps protection stable.
- Make primary selection strictly minimize time-to-full-protection: choose the k drones with smallest arrival times, but prefer keepers and movers and only move drones under the hold restriction if necessary. If primary cannot be fully protected by moveable drones, allow overriding hold for the minimal number needed.
- Lock fully-protected fields (do not steal drones from them).
- For other fields, allocate only from truly available drones (not held), preferring to fully protect fields with the best value (threat/k). Do not steal from locked fields.
- Preposition remaining available drones near the field for which arrival_time / threat is minimal (so they will arrive fast if that field becomes urgent later).
- Enforce move limits (change at most floor(N/2) drones) but always allow necessary moves to secure the primary.
- Track last assignment-step per drone so hold-time works correctly; when a drone is moved its last-assigned-step updates.

The code below implements the strategy in class SmartFarmAdaptation.

```py
from typing import Dict, Any, List, Set
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0
    HOLD_TIME = 3  # number of steps to keep a protecting assignment before moving the drone unless primary requires it

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map drone id -> last assignment group we've commanded
        self.prev_assignments: Dict[int, str] = {}
        # Map drone id -> consecutive steps in same group
        self.stable_steps: Dict[int, int] = {}
        # Map drone id -> step when last assignment change happened (used for hold-time)
        self.assign_step: Dict[int, int] = {}
        self.last_step = -1

    def _dist_to_field(self, loc, field) -> float:
        x, y = loc.x, loc.y
        cx = min(max(x, field.left), field.right)
        cy = min(max(y, field.top), field.bottom)
        return math.hypot(x - cx, y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        N = len(drones)
        if N == 0:
            return

        half_min = math.ceil(N / 2)
        change_limit = N // 2  # prefer not to change more than half

        # Threatened fields we can protect
        threat_fields = [f for f in environment.fields if f.threat_level > 0 and f'protecting {f.id}' in group_ids]
        field_by_group = {f'protecting {f.id}': f for f in threat_fields}

        # If no threats -> idle all
        if not threat_fields:
            for comp in drones:
                environment.assign_group(comp, 'idle')
                key = id(comp)
                if self.prev_assignments.get(key) == 'idle':
                    self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
                else:
                    self.stable_steps[key] = 0
                    # update assign_step only when group changed
                self.prev_assignments[key] = 'idle'
            self.last_step = step
            return

        # Infer current group for each drone (prefer our last commanded assignment if still valid)
        current_group_for: Dict[Any, str] = {}
        for comp in drones:
            key = id(comp)
            prev = self.prev_assignments.get(key)
            if prev in group_ids:
                current_group_for[comp] = prev
            else:
                tid = getattr(comp, 'target_id', None)
                if tid:
                    grp = f'protecting {tid}'
                    current_group_for[comp] = grp if grp in group_ids else 'idle'
                else:
                    current_group_for[comp] = 'idle'

        # Update stability counters (based on previous assignment we commanded)
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            prev = self.prev_assignments.get(key)
            if prev == curr:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0

        # Required drones per field (ceil)
        required_map = {f'protecting {f.id}': max(0, math.ceil(f.drones_for_full_protection)) for f in threat_fields}

        # Current counts per protecting group
        current_counts = defaultdict(int)
        for comp in drones:
            current_counts[current_group_for[comp]] += 1

        # Lock fields that are already fully protected (do not steal from them)
        locked_fields: Set[str] = set()
        locked_drones: Set[int] = set()
        for f in threat_fields:
            grp = f'protecting {f.id}'
            req = required_map.get(grp, 0)
            if req > 0 and current_counts.get(grp, 0) >= req:
                locked_fields.add(grp)
                for comp in drones:
                    if current_group_for[comp] == grp:
                        locked_drones.add(id(comp))

        # Primary (highest threat)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = min(required_map.get(primary_group, 0), N)

        # arrival helper
        def arrival_time(comp, field):
            return self._dist_to_field(comp.location, field) / self.DRONE_SPEED

        # determine if a drone is allowed to be moved under hold-time rules
        def is_moveable(comp):
            key = id(comp)
            # idle drones are readily moveable
            if current_group_for[comp] == 'idle':
                return True
            # if this drone is locked, not moveable
            if key in locked_drones:
                return False
            # if we never set assign_step, assume moveable
            last = self.assign_step.get(key)
            if last is None:
                return True
            # If enough steps have passed since last assignment-change, moveable
            if (step - last) >= self.HOLD_TIME:
                return True
            return False

        # Ranking key for selecting drones for a field:
        # prefer keepers (already protecting that field), then movers to that field,
        # then moveable idle, then other moveable drones with low stability and small arrival.
        def rank_key(comp, field, group_name):
            key = id(comp)
            keeper = 0 if current_group_for[comp] == group_name else 1
            mover = 0 if (getattr(comp, 'state', '') == 'moving_to_field' and getattr(comp, 'target_id', None) == field.id) else 1
            idle = 0 if current_group_for[comp] == 'idle' else 1
            mov = 0 if is_moveable(comp) else 1  # prefer moveable (lower)
            stab = self.stable_steps.get(key, 0)
            arr = arrival_time(comp, field)
            # score tuple to sort ascending
            return (keeper, mover, idle, mov, stab, arr, key % 997)

        # select up to k drones for a field from candidates, respecting locked drones and hold-time except if allow_override True
        def select_k(field, group_name, k, allow_override=False):
            # Candidates are all drones, but keepers always eligible
            candidates = []
            for comp in drones:
                key = id(comp)
                # if comp is locked and not keeper, skip unless override allowed
                if key in locked_drones and current_group_for[comp] != group_name:
                    if not allow_override:
                        continue
                candidates.append(comp)
            # sort by rank key
            candidates.sort(key=lambda c: rank_key(c, field, group_name))
            # pick first k but if we don't allow override, ensure we only pick moveable or keepers
            selected = []
            for c in candidates:
                if len(selected) >= k:
                    break
                if current_group_for[c] == group_name:
                    selected.append(c)
                    continue
                if is_moveable(c):
                    selected.append(c)
                    continue
                # if not moveable but override allowed, pick it (we'll try to minimize such picks)
                if allow_override:
                    selected.append(c)
                    continue
                # else skip
            return selected[:k]

        desired: Dict[int, str] = {}
        # Reserve locked drones first
        for comp in drones:
            key = id(comp)
            if key in locked_drones:
                desired[key] = current_group_for[comp]

        # Available set = drones not locked and not already reserved
        available = set(comp for comp in drones if id(comp) not in locked_drones)

        # Primary allocation: try to fill primary using only moveable drones + keepers.
        if primary_group in locked_fields:
            # primary already locked: keep keepers
            for comp in drones:
                if current_group_for[comp] == primary_group:
                    desired[id(comp)] = primary_group
                    if comp in available:
                        available.discard(comp)
        else:
            selected_primary = select_k(primary_field, primary_group, required_primary, allow_override=False)
            # If insufficient (e.g., too many drones under hold), allow minimal override to reach required_primary
            if len(selected_primary) < required_primary:
                # compute how many more needed
                need = required_primary - len(selected_primary)
                # select again allowing override (may choose unmoveable drones), but sort prefers minimal override
                extra = select_k(primary_field, primary_group, required_primary, allow_override=True)
                # merge, preserving order and uniqueness
                ids = {id(c) for c in selected_primary}
                for c in extra:
                    if len(selected_primary) >= required_primary:
                        break
                    if id(c) not in ids:
                        selected_primary.append(c)
                        ids.add(id(c))
            # assign selected_primary
            for c in selected_primary[:required_primary]:
                desired[id(c)] = primary_group
                if c in available:
                    available.discard(c)

        # For other fields, greedily protect full fields by descending (threat / k) using available drones only (don't override hold/locked)
        other_fields = [f for f in threat_fields if f.id != primary_field.id]
        other_fields.sort(key=lambda f: (f.threat_level / max(1.0, max(1, math.ceil(f.drones_for_full_protection)))), reverse=True)

        for f in other_fields:
            grp = f'protecting {f.id}'
            if grp in locked_fields:
                # keep locked drones
                for comp in drones:
                    if current_group_for[comp] == grp:
                        desired[id(comp)] = grp
                        if comp in available:
                            available.discard(comp)
                continue
            k = required_map.get(grp, 0)
            if k <= 0:
                continue
            # count already planned
            already_planned = sum(1 for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp)
            need = max(0, k - already_planned)
            if need <= 0:
                continue
            # pick need from available pool; keepers are allowed even if not in available
            pool = set(available) | {comp for comp in drones if current_group_for[comp] == grp}
            # select_k will filter locked drones out unless override True; here we do not allow override
            # But ensure selection draws mostly from pool by filtering results
            candidates = select_k(f, grp, k, allow_override=False)
            # retain only those in pool or keepers
            picks = []
            for c in candidates:
                if len(picks) >= need:
                    break
                if c in pool or current_group_for[c] == grp:
                    picks.append(c)
            # If still not enough picks, we do not override locked drones; leave unprotected
            for c in picks:
                desired[id(c)] = grp
                if c in available:
                    available.discard(c)

        # After filling full protections, preposition remaining available drones to fields where arrival_time / threat is minimal
        remaining = [comp for comp in drones if id(comp) not in desired]
        for comp in remaining:
            best = None
            best_score = float('inf')
            for f in threat_fields:
                grp = f'protecting {f.id}'
                # skip if field has zero capacity (k==0)
                if required_map.get(grp, 0) <= 0:
                    continue
                arr = arrival_time(comp, f)
                # score: arrival / threat (lower preferred)
                score = arr / max(0.001, f.threat_level)
                if score < best_score:
                    best_score = score
                    best = f
            if best is not None:
                desired[id(comp)] = f'protecting {best.id}'
            else:
                desired[id(comp)] = 'idle'

        # Ensure no overprotection (cap assignments at required_map)
        for grp, cap in required_map.items():
            assigned = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp]
            if len(assigned) <= cap:
                continue
            # keep those already in group and with higher stability
            assigned.sort(key=lambda c: (0 if current_group_for[c] == grp else 1, -self.stable_steps.get(id(c), 0)))
            keep = assigned[:cap]
            drop = assigned[cap:]
            for c in drop:
                desired[id(c)] = 'idle'

        # Now compute which drones would change and enforce change_limit while always allowing necessary primary moves
        would_change = []
        would_keep = []
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            targ = desired.get(key, 'idle')
            if targ not in group_ids:
                targ = 'idle'
                desired[key] = 'idle'
            if targ != curr:
                would_change.append((comp, curr, targ))
            else:
                would_keep.append((comp, curr, targ))

        # Critical: changes that move a drone into primary_group
        critical_changes = [c for c in would_change if c[2] == primary_group]
        non_critical_changes = [c for c in would_change if c[2] != primary_group]

        # Build final_assignment starting with current groups
        final_assignment: Dict[int, str] = {id(comp): current_group_for[comp] for comp in drones}

        # Apply all critical changes (ensure primary fully protected)
        for comp, curr, targ in critical_changes:
            final_assignment[id(comp)] = targ

        used_changes = len(critical_changes)
        remaining_slots = max(0, change_limit - used_changes)

        # Choose non-critical changes to allow: pick drones with low stability and not currently protecting (prefer moving idle/movers)
        def noncrit_key(item):
            comp, curr, targ = item
            key = id(comp)
            stab = self.stable_steps.get(key, 0)
            protecting_now = 1 if curr.startswith('protecting ') else 0
            # distance penalty to target for preference
            dist = 0.0
            if targ.startswith('protecting '):
                tid = targ.replace('protecting ', '')
                fobj = next((ff for ff in threat_fields if ff.id == tid), None)
                if fobj:
                    dist = self._dist_to_field(comp.location, fobj)
            return (stab, protecting_now, dist, key % 997)

        non_critical_changes.sort(key=noncrit_key)
        allowed_noncrit = non_critical_changes[:remaining_slots]
        allowed_ids = set(id(item[0]) for item in allowed_noncrit)

        for comp, curr, targ in non_critical_changes:
            if id(comp) in allowed_ids:
                final_assignment[id(comp)] = targ
            else:
                final_assignment[id(comp)] = curr if curr in group_ids else 'idle'
        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # Ensure primary fully protected in final (override if necessary)
        final_primary_count = sum(1 for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) == primary_group)
        if final_primary_count < required_primary:
            need = required_primary - final_primary_count
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), arrival_time(c, primary_field)))
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group

        # Final cap enforcement (again)
        final_groups = defaultdict(list)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_groups[grp].append(comp)
        for grp, comps in final_groups.items():
            if grp.startswith('protecting ') and grp in required_map:
                cap = required_map[grp]
                if len(comps) > cap:
                    comps.sort(key=lambda c: (0 if current_group_for[c] == grp else 1, -self.stable_steps.get(id(c), 0)))
                    for c in comps[cap:]:
                        final_assignment[id(c)] = 'idle'

        # Apply assignments and update tracking (prev_assignments, stable_steps, assign_step)
        for comp in drones:
            key = id(comp)
            assigned_group = final_assignment.get(key, current_group_for[comp])
            if assigned_group not in group_ids:
                assigned_group = 'idle'
            environment.assign_group(comp, assigned_group)
            prev = self.prev_assignments.get(key)
            # update stable_steps
            if prev == assigned_group:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0
                # record the step when assignment changed
                self.assign_step[key] = step
            # store commanded assignment
            self.prev_assignments[key] = assigned_group

        self.last_step = step
```