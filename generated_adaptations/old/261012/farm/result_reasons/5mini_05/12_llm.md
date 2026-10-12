Reasoning and improved strategy

What I'll change now

- Use arrival time (distance / speed) as the main driver for decisions: a field is only protected once all assigned drones arrive, so the time-to-full-protection is the max arrival among those drones. Fields that can be fully protected quickly and have high threat should get priority.
- When selecting drones for a field, consider drones already protecting that field (arrival 0) and drones already moving toward it first — they reduce both required moves and time to protection.
- For each field compute a "benefit-per-drone" metric:
    benefit_per_drone = threat_level / (k * (time_to_protect + epsilon))
  where k is the field's drones_for_full_protection (ceil). This favors high-threat, small-k, fast-to-protect fields.
- Always fully protect the primary (highest-threat) field with the drones that minimize the primary's time-to-protection (i.e., the k drones with smallest arrival times, preferring those already there).
- Greedily select other fields by benefit_per_drone while drones remain.
- Prefer to move drones with low stability. When the number of planned changes exceeds the allowed churn (floor(N/2)), revert some non-essential moves — specifically those with high stability and high movement cost (distance / speed) — unless reverting would leave the primary unprotected.
- Enforce no overprotection (cap assignments at ceil(drones_for_full_protection)).
- Ensure at least half of drones are assigned to protection if field capacities allow it by filling remaining capacity by highest benefit.
- Track previous assignments and per-drone stability to reduce unnecessary churn going forward.

This approach focuses on minimizing the time until fields get fully protected weighted by threat, which reduces how long birds can inflict damage before protection completes, while still respecting stability and churn limits.

Code

```py
from typing import Dict, Any, List, Tuple
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0  # drone speed as specified

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map drone id -> last assignment we made
        self.prev_assignments: Dict[int, str] = {}
        # Map drone id -> consecutive steps in same group
        self.stable_steps: Dict[int, int] = {}
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
        move_limit = N // 2  # prefer not to change more than half each step

        # collect threatful fields whose group exists
        threat_fields = [f for f in environment.fields if f.threat_level > 0 and f'protecting {f.id}' in group_ids]
        field_by_group = {f'protecting {f.id}': f for f in threat_fields}

        # if no threats, idle all drones
        if not threat_fields:
            for comp in drones:
                environment.assign_group(comp, 'idle')
                key = id(comp)
                if self.prev_assignments.get(key) == 'idle':
                    self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
                else:
                    self.stable_steps[key] = 0
                self.prev_assignments[key] = 'idle'
            self.last_step = step
            return

        # infer current group for each drone (prefer our previous assignment)
        current_group_for: Dict[Any, str] = {}
        for comp in drones:
            key = id(comp)
            prev = self.prev_assignments.get(key)
            if prev in group_ids:
                current_group_for[comp] = prev
                continue
            tid = getattr(comp, 'target_id', None)
            if tid:
                grp = f'protecting {tid}'
                current_group_for[comp] = grp if grp in group_ids else 'idle'
            else:
                current_group_for[comp] = 'idle'

        # update stability counters
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            prev = self.prev_assignments.get(key)
            if prev == curr:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0

        # primary field = highest threat (tie-break by id)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_map = {f'protecting {f.id}': max(0, math.ceil(f.drones_for_full_protection)) for f in threat_fields}
        required_primary = min(required_map.get(primary_group, 0), N)

        # Precompute arrival times for all drones to each field on demand
        def arrival_time(comp, field) -> float:
            return self._dist_to_field(comp.location, field) / self.DRONE_SPEED

        # Candidate ranking for a field: prefer already-there (arrival 0), then moving_to_field, then idle, then others.
        # But the main sort key is arrival time; use stability as a small penalty to avoid moving very stable drones.
        def rank_candidates(field, candidates: List[Any]) -> List[Any]:
            scored = []
            for c in candidates:
                key = id(c)
                arr = arrival_time(c, field)
                score = arr
                # strongly prefer ones already assigned to the field
                if current_group_for[c] == f'protecting {field.id}':
                    score -= 10000.0
                # prefer those moving to the same target
                if getattr(c, 'state', '') == 'moving_to_field' and getattr(c, 'target_id', None) == field.id:
                    score -= 2000.0
                # small penalty for high stability (avoid moving stable drones)
                stab = self.stable_steps.get(key, 0)
                score += stab * 0.5
                # tie-break determinism
                score += (key % 997) * 1e-6
                scored.append((score, c))
            scored.sort(key=lambda x: x[0])
            return [c for _, c in scored]

        # For each field compute the optimal k drones (k = required_map[field]) from the full drone set that minimize max arrival
        # We'll build a candidate plan: always include primary; then greedily include other fields by benefit_per_drone metric.
        unallocated = set(drones)
        desired: Dict[int, str] = {}

        # Function to pick best k drones for a field from available pool (but prefer ones already there even if not in pool)
        def best_k_for_field(field, k, available_pool: List[Any]) -> List[Any]:
            # build candidate list including drones already in the field even if not in available_pool,
            # because keeping them is free (we consider them as available)
            # but to avoid duplications, we consider all drones but later we only take those not already allocated elsewhere
            all_candidates = list(drones)
            ranked = rank_candidates(field, all_candidates)
            chosen = []
            for c in ranked:
                if len(chosen) >= k:
                    break
                # we will choose even if already assigned elsewhere; allocation conflict resolved later by greedy order
                chosen.append(c)
            return chosen

        # Always allocate primary using drones that minimize primary time-to-protect (k with smallest arrivals)
        primary_candidates_sorted = rank_candidates(primary_field, drones)
        primary_selected = primary_candidates_sorted[:required_primary]
        # mark selected primary drones
        for c in primary_selected:
            desired[id(c)] = primary_group
            if c in unallocated:
                unallocated.remove(c)

        # Greedy selection for other fields by benefit_per_drone
        # Compute for each field (except primary) the best k drones and its time-to-protect and benefit_per_drone
        field_infos: List[Tuple[float, str, Any, List[Any]]] = []
        for f in threat_fields:
            grp = f'protecting {f.id}'
            if grp == primary_group:
                continue
            k = required_map.get(grp, 0)
            if k <= 0 or k > N:
                continue
            # choose best k from all drones (we will allocate only from unallocated later)
            candidate_list = rank_candidates(f, drones)
            best_k = candidate_list[:k]
            ttp = 0.0
            if best_k:
                ttp = max(arrival_time(c, f) for c in best_k)
            # small epsilon to avoid div by zero
            eps = 0.05
            benefit_per_drone = f.threat_level / (k * (ttp + eps))
            field_infos.append((benefit_per_drone, grp, f, best_k))
        # sort descending benefit_per_drone
        field_infos.sort(key=lambda x: x[0], reverse=True)

        # allocate greedily while drones remain: when allocating a field, we actually pick the best available drones for it,
        # preferring already-in-field and shorter arrival among available_pool
        for benefit, grp, field_obj, _best_k in field_infos:
            k = required_map.get(grp, 0)
            # compute how many already will be assigned to this group in desired or are currently there and not reassignable
            already = sum(1 for comp in drones if (desired.get(id(comp)) == grp) or (id(comp) not in desired and current_group_for[comp] == grp))
            need = max(0, k - already)
            if need <= 0:
                continue
            # choose from unallocated pool ranked for this field
            pool = list(unallocated)
            if not pool:
                break
            ranked_pool = rank_candidates(field_obj, pool)
            take = ranked_pool[:need]
            for c in take:
                desired[id(c)] = grp
                if c in unallocated:
                    unallocated.remove(c)

        # After filling full protections, count protecting_count
        protecting_count = sum(1 for g in desired.values() if g.startswith('protecting '))
        protecting_count += sum(1 for comp in drones if id(comp) not in desired and current_group_for[comp].startswith('protecting '))
        # If less than half_min, try to fill remaining capacities ordered by benefit (we recompute capacities)
        if protecting_count < half_min:
            need_more = half_min - protecting_count
            # compute current planned assigned counts
            assigned_counts = defaultdict(int)
            for comp in drones:
                grp = desired.get(id(comp), current_group_for[comp])
                assigned_counts[grp] += 1
            # compute capacities and benefit metric for each field
            caps = []
            for f in threat_fields:
                grp = f'protecting {f.id}'
                cap = max(0, required_map.get(grp, 0) - assigned_counts.get(grp, 0))
                if cap <= 0:
                    continue
                # estimate time-to-protect using best available unallocated
                pool = list(unallocated)
                if not pool:
                    # if no unallocated, break
                    continue
                ranked = rank_candidates(f, pool)[:cap]
                ttp = 0.0
                if ranked:
                    ttp = max(arrival_time(c, f) for c in ranked)
                benefit_per_drone = f.threat_level / (cap * (ttp + 0.05))
                caps.append((benefit_per_drone, f, grp, cap, ranked))
            caps.sort(key=lambda x: x[0], reverse=True)
            for bpd, f, grp, cap, ranked in caps:
                if need_more <= 0:
                    break
                take = ranked[:min(cap, need_more)]
                for c in take:
                    desired[id(c)] = grp
                    if c in unallocated:
                        unallocated.remove(c)
                    need_more -= 1

        # Any still unallocated: prefer to keep current protecting assignment if valid and not over cap; otherwise idle
        assigned_counts = defaultdict(int)
        for comp in drones:
            grp = desired.get(id(comp), current_group_for[comp])
            assigned_counts[grp] += 1
        for comp in list(unallocated):
            curr = current_group_for[comp]
            assign = None
            if curr.startswith('protecting '):
                cap = required_map.get(curr, 0)
                if assigned_counts.get(curr, 0) < cap:
                    assign = curr
            if assign is None:
                assign = 'idle'
            desired[id(comp)] = assign
            assigned_counts[assign] += 1
            unallocated.remove(comp)

        # enforce no overprotection: if any group exceeds its cap, drop lowest-priority assigned drones to idle
        for grp, cap in required_map.items():
            assigned_list = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp]
            if len(assigned_list) <= cap:
                continue
            # keep those already there and with higher stability
            def keep_score(c):
                key = id(c)
                was_here = 1 if current_group_for[c] == grp else 0
                stab = self.stable_steps.get(key, 0)
                # prefer higher was_here and higher stability
                return (-was_here, -stab, self._dist_to_field(c.location, field_by_group.get(grp, primary_field)))
            assigned_list.sort(key=keep_score)
            keep = assigned_list[:cap]
            drop = assigned_list[cap:]
            for c in drop:
                desired[id(c)] = 'idle'

        # Now compute which drones would change
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

        # Identify critical moves (those that assign to primary) and ensure primary is fully protected
        critical = [c for c in would_change if c[2] == primary_group]
        non_critical = [c for c in would_change if c[2] != primary_group]

        # If primary won't be fully protected in desired, force additional assignments (shouldn't happen)
        planned_primary = sum(1 for comp in drones if desired.get(id(comp), current_group_for[comp]) == primary_group)
        if planned_primary < required_primary:
            need = required_primary - planned_primary
            # pick best candidates not already primary sorted by arrival and low stability
            candidates = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), arrival_time(c, primary_field)))
            for c in candidates[:need]:
                desired[id(c)] = primary_group
            # recompute would_change lists
            would_change = []
            would_keep = []
            for comp in drones:
                key = id(comp)
                curr = current_group_for[comp]
                targ = desired.get(key, 'idle')
                if targ != curr:
                    would_change.append((comp, curr, targ))
                else:
                    would_keep.append((comp, curr, targ))
            critical = [c for c in would_change if c[2] == primary_group]
            non_critical = [c for c in would_change if c[2] != primary_group]

        # Enforce change limit but allow critical moves even if they exceed limit
        final_assignment: Dict[int, str] = {id(comp): current_group_for[comp] for comp in drones}
        # apply all critical changes
        for comp, curr, targ in critical:
            final_assignment[id(comp)] = targ

        used_changes = len(critical)
        remaining_slots = max(0, move_limit - used_changes) if used_changes <= move_limit else 0

        # choose which non-critical changes to allow based on willingness: prefer low stability and small arrival to target
        def noncrit_metric(item):
            comp, curr, targ = item
            key = id(comp)
            stab = self.stable_steps.get(key, 0)
            # prefer to move those not currently protecting
            protecting_now = 1 if curr.startswith('protecting ') else 0
            # distance penalty to target
            dist = 0.0
            if targ.startswith('protecting '):
                field_obj = field_by_group.get(targ, None)
                if field_obj:
                    dist = self._dist_to_field(comp.location, field_obj)
            return (stab, protecting_now, dist)
        non_critical.sort(key=noncrit_metric)

        allowed_noncrit = non_critical[:remaining_slots]
        allowed_noncrit_set = set(id(item[0]) for item in allowed_noncrit)

        for comp, curr, targ in non_critical:
            if id(comp) in allowed_noncrit_set:
                final_assignment[id(comp)] = targ
            else:
                final_assignment[id(comp)] = curr if curr in group_ids else 'idle'

        # keep the ones that would keep
        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # ensure primary is still fully protected; if not, force additional moves (override)
        final_count_primary = sum(1 for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) == primary_group)
        if final_count_primary < required_primary:
            need = required_primary - final_count_primary
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), arrival_time(c, primary_field)))
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group

        # final cap enforcement
        final_groups = defaultdict(list)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_groups[grp].append(comp)
        for grp, comps in final_groups.items():
            if grp.startswith('protecting ') and grp in required_map:
                cap = required_map[grp]
                if len(comps) > cap:
                    # keep best ones
                    comps.sort(key=lambda c: (-1 if current_group_for[c] == grp else 0, -self.stable_steps.get(id(c), 0)))
                    keep = comps[:cap]
                    drop = comps[cap:]
                    for c in drop:
                        final_assignment[id(c)] = 'idle'

        # Apply final assignments and update tracking
        for comp in drones:
            key = id(comp)
            grp = final_assignment.get(key, current_group_for[comp])
            if grp not in group_ids:
                grp = 'idle'
            environment.assign_group(comp, grp)
            prev = self.prev_assignments.get(key)
            if prev == grp:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0
            self.prev_assignments[key] = grp

        self.last_step = step
```