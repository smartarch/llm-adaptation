Reasoning and strategy

Summary of goals and lessons from previous attempts
- The most important rule is strict: always fully protect the single most threatened field, and do so with the drones that get there soonest.
- Avoid overprotecting fields. Prefer fully protecting fewer fields than partially protecting many.
- Prefer to keep drones that are already protecting a field (stability), but not at the cost of leaving the primary field unprotected.
- When stealing drones from other fields to protect the primary, avoid taking drones that would break protection of another high-threat field. Prefer taking from over-protected or low-threat fields and from drones with low stability.
- Use arrival time (distance / speed) as the main metric for how quickly a drone helps a field; choose the k drones with the smallest arrival times for a field, but respect donor-penalty rules when selecting from already-protecting drones.
- Try to use at least half the fleet for protection when capacity allows.
- Limit churn (number of drones changing groups) unless necessary to secure the primary field.

Adaptation strategy implemented here
1. Determine current inferred group for each drone (prefer our previous assignment if still valid).
2. Compute required_map = ceil(drones_for_full_protection) for each threatened field.
3. Find primary field (highest threat_level) and choose required_primary drones for it:
   - Prefer drones already protecting primary (arrival ~0), then moving-to-primary, then idle drones.
   - If more drones are needed, consider stealing from other fields but compute a donor penalty for each candidate: removing a drone that causes another field to drop below its required protection gets a high penalty (proportional to that field's threat), removing from a field with surplus is cheap. Also prefer low-stability donors and shorter arrival to primary.
   - Select the k drones that minimize (penalty, arrival_time, stability).
4. For other fields (sorted by threat descending), fill them to their required capacity using remaining drones; prefer keepers, movers, idle, then steal only from low-penalty donors.
5. If after full protections fewer than half of the drones are protecting and there is remaining capacity on fields, fill capacity by benefit (threat / time-to-protect) up to half the fleet.
6. If still not at half and no capacity, assign remaining drones as idle (do not overprotect).
7. Compute planned changes versus current groups; enforce a change limit (floor(N/2)) but always allow the moves necessary to secure the primary field. When forced to keep some drones in place to respect change limit, prefer to keep those with high stability and those that would cause large penalty if removed.
8. Apply assignments with environment.assign_group and update per-drone stability tracking.

This approach aims to (a) guarantee primary protection quickly by using the fastest available drones, (b) avoid breaking protection on other important fields, and (c) reduce churn by preferring stable protectors unless there's a strong reason to move them.

Code

```py
from typing import Dict, Any, List, Tuple
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assignments: Dict[int, str] = {}
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
        change_limit = N // 2  # prefer not to change more than half

        # Fields that require protecting
        threat_fields = [f for f in environment.fields if f.threat_level > 0 and f'protecting {f.id}' in group_ids]
        field_by_group = {f'protecting {f.id}': f for f in threat_fields}

        # If no threats, idle all drones
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

        # Determine current group for each drone (prefer our last commanded assignment if still valid)
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

        # Update stability counters
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            prev = self.prev_assignments.get(key)
            if prev == curr:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0

        # Required drones per field
        required_map = {f'protecting {f.id}': max(0, math.ceil(f.drones_for_full_protection)) for f in threat_fields}

        # Primary field selection
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = min(required_map.get(primary_group, 0), N)

        # Helpers
        def arrival_time(comp, field) -> float:
            return self._dist_to_field(comp.location, field) / self.DRONE_SPEED

        # Compute current assigned count per group (based on current_group_for)
        current_counts = defaultdict(int)
        for comp in drones:
            grp = current_group_for[comp]
            current_counts[grp] += 1

        # Build donor info for each drone if it's protecting another field
        # donor_penalty(comp): if removing comp would cause its field's assigned count to drop below required, penalty = 100 * threat,
        # else penalty = threat * 1.0; for idle or moving drones penalty = 0.
        def donor_penalty(comp) -> float:
            grp = current_group_for[comp]
            if not grp.startswith('protecting '):
                return 0.0
            field = field_by_group.get(grp)
            if field is None:
                return 0.0
            assigned = current_counts.get(grp, 0)
            required = required_map.get(grp, 0)
            # if removing would break protection
            if assigned - 1 < required:
                return 100.0 * field.threat_level
            # else cost proportional to field threat (lower is better)
            return 1.0 * field.threat_level

        # Build candidate scoring for selecting drones for a target field
        # Score: (penalty, arrival_time, stability) -> lower is better
        def score_for_target(comp, target_field, prefer_keep_group=None) -> Tuple[float, float, int]:
            pen = donor_penalty(comp)
            arr = arrival_time(comp, target_field)
            stab = self.stable_steps.get(id(comp), 0)
            # if comp already in the target group, give a strong bonus (reduce score)
            if current_group_for[comp] == prefer_keep_group:
                pen -= 50.0  # prefer keepers strongly
            return (pen, arr, stab)

        # Select k drones for a field minimizing (penalty, arrival, stability), but prefer already-there, movers, idle.
        def select_k_for_field(field, k, available_set: set, allow_steal=True) -> List[Any]:
            # Candidate list is all drones; but we will prioritize those in available_set first (idle, movers, etc.)
            candidates = list(drones)
            scored = []
            for c in candidates:
                # If not allowing steal, deprioritize drones that are protecting other fields (i.e., high donor penalty)
                if not allow_steal and current_group_for[c].startswith('protecting ') and current_group_for[c] != f'protecting {field.id}':
                    # give huge penalty
                    pen = donor_penalty(c) + 1000.0
                    arr = arrival_time(c, field)
                    stab = self.stable_steps.get(id(c), 0)
                    scored.append((pen, arr, stab, c))
                else:
                    pen, arr, stab = score_for_target(c, field, prefer_keep_group=f'protecting {field.id}')
                    scored.append((pen, arr, stab, c))
            # sort by tuple
            scored.sort(key=lambda x: (x[0], x[1], x[2]))
            chosen = []
            for _, _, _, c in scored:
                # only pick if available or if we allow steal
                if c in available_set or allow_steal:
                    chosen.append(c)
                if len(chosen) >= k:
                    break
            return chosen[:k]

        desired: Dict[int, str] = {}
        unallocated = set(drones)

        # Step 1: Primary allocation - must always be fully protected.
        # Prefer not to steal from other fields unless necessary, but ensure we get required_primary drones.
        # Try in order: keepers, movers, idles, steal low-penalty donors.
        # We'll build pools:
        primary_keepers = [c for c in drones if current_group_for[c] == primary_group]
        primary_movers = [c for c in drones if getattr(c, 'state', '') == 'moving_to_field' and getattr(c, 'target_id', None) == primary_field.id and current_group_for[c] != primary_group]
        primary_idles = [c for c in drones if current_group_for[c] == 'idle']
        # start collecting
        primary_selected = []
        for c in primary_keepers:
            if len(primary_selected) >= required_primary:
                break
            primary_selected.append(c)
        for c in primary_movers:
            if len(primary_selected) >= required_primary:
                break
            if c not in primary_selected:
                primary_selected.append(c)
        for c in primary_idles:
            if len(primary_selected) >= required_primary:
                break
            if c not in primary_selected:
                primary_selected.append(c)
        # If still need more, consider other drones; select_k_for_field with allow_steal True will choose best donors by penalty
        if len(primary_selected) < required_primary:
            need = required_primary - len(primary_selected)
            # available_set includes idles, movers, keepers (we've already used them), but select_k_for_field will consider all and choose minimal penalty
            candidates = select_k_for_field(primary_field, need, set(primary_selected) | set(primary_idles) | set(primary_movers) | set(primary_keepers), allow_steal=True)
            for c in candidates:
                if c not in primary_selected:
                    primary_selected.append(c)
        # Mark desired
        for c in primary_selected[:required_primary]:
            desired[id(c)] = primary_group
            if c in unallocated:
                unallocated.remove(c)
            # update current_counts as if we've reserved them (so donor_penalty calculations change for later selections)
            current_counts[current_group_for[c]] -= 1
            current_counts[primary_group] += 1

        # Step 2: Greedily allocate other fields by descending threat, filling to required where possible.
        other_fields = sorted([f for f in threat_fields if f.id != primary_field.id], key=lambda f: f.threat_level, reverse=True)
        for f in other_fields:
            grp = f'protecting {f.id}'
            req = required_map.get(grp, 0)
            planned = sum(1 for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp)
            need = max(0, req - planned)
            if need <= 0:
                continue
            # Prefer not to steal from fields with higher or equal threat; allow stealing from low-threat fields
            allow_steal = True
            # Build available set: those not already desired for other groups
            avail = set(unallocated)
            # pick best for this field
            pick = select_k_for_field(f, need, avail, allow_steal=True)
            for c in pick:
                if id(c) in desired:
                    continue
                desired[id(c)] = grp
                if c in unallocated:
                    unallocated.remove(c)
                # update current_counts as they're now reserved
                current_counts[current_group_for[c]] -= 1
                current_counts[grp] += 1

        # Step 3: Ensure at least half of drones are protecting when capacity allows
        protecting_count = sum(1 for g in desired.values() if g.startswith('protecting '))
        protecting_count += sum(1 for comp in drones if id(comp) not in desired and current_group_for[comp].startswith('protecting '))
        if protecting_count < half_min:
            need_more = half_min - protecting_count
            # compute remaining capacities
            assigned_counts = defaultdict(int)
            for comp in drones:
                grp = desired.get(id(comp), current_group_for[comp])
                assigned_counts[grp] += 1
            capacities = []
            for f in threat_fields:
                g = f'protecting {f.id}'
                cap = max(0, required_map.get(g, 0) - assigned_counts.get(g, 0))
                if cap > 0:
                    capacities.append((f.threat_level, f, g, cap))
            capacities.sort(key=lambda x: x[0], reverse=True)
            for _, field, grp, cap in capacities:
                if need_more <= 0:
                    break
                # take closest unallocated
                pool = list(unallocated)
                pool.sort(key=lambda c: self._dist_to_field(c.location, field))
                take = min(cap, need_more)
                for c in pool[:take]:
                    desired[id(c)] = grp
                    if c in unallocated:
                        unallocated.remove(c)
                    need_more -= 1

        # Any remaining unallocated: prefer to keep current protecting assignment if valid and not over cap, else idle
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

        # Enforce no overprotection: if any group exceeds its required cap, trim least-desirable assigned drones
        for grp, cap in required_map.items():
            assigned_list = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp]
            if len(assigned_list) <= cap:
                continue
            # sort by keep preference: prefer those who were already in that group and higher stability
            assigned_list.sort(key=lambda c: (0 if current_group_for[c] == grp else 1, -self.stable_steps.get(id(c), 0)))
            keep = assigned_list[:cap]
            drop = assigned_list[cap:]
            for c in drop:
                desired[id(c)] = 'idle'

        # Compute changes and enforce change limit; but always allow changes necessary for primary drones
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

        # Identify primary-related changes
        primary_changes = [c for c in would_change if c[2] == primary_group]
        non_primary_changes = [c for c in would_change if c[2] != primary_group]

        # We must allow all primary_changes to ensure the field is fully protected
        final_assignment: Dict[int, str] = {id(comp): current_group_for[comp] for comp in drones}
        for comp, curr, targ in primary_changes:
            final_assignment[id(comp)] = targ

        used_changes = len(primary_changes)
        remaining_slots = max(0, change_limit - used_changes)

        # Select non-primary changes to allow (prefer low stability and low donor penalty)
        def nonprim_key(item):
            comp, curr, targ = item
            k = id(comp)
            stab = self.stable_steps.get(k, 0)
            pen = donor_penalty(comp)
            # prefer lower penalty, lower stability
            return (pen, stab, self._dist_to_field(comp.location, field_by_group.get(targ, primary_field)))

        non_primary_changes.sort(key=nonprim_key)
        allowed_nonprimary = non_primary_changes[:remaining_slots]
        allowed_set = set(id(item[0]) for item in allowed_nonprimary)

        for comp, curr, targ in non_primary_changes:
            if id(comp) in allowed_set:
                final_assignment[id(comp)] = targ
            else:
                final_assignment[id(comp)] = curr if curr in group_ids else 'idle'
        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # Sanity: ensure primary ended up with required_primary in final_assignment; if not, override by forcing more changes
        final_primary_count = sum(1 for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) == primary_group)
        if final_primary_count < required_primary:
            need = required_primary - final_primary_count
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            # sort candidates by minimal (donor_penalty, arrival_time, stability)
            candidates.sort(key=lambda c: (donor_penalty(c), arrival_time(c, primary_field), self.stable_steps.get(id(c), 0)))
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group

        # Final overprotection check & correction
        final_counts = defaultdict(list)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_counts[grp].append(comp)
        for grp, comps in final_counts.items():
            if grp.startswith('protecting ') and grp in required_map:
                cap = required_map[grp]
                if len(comps) > cap:
                    # keep best ones (those already there and with higher stability)
                    comps.sort(key=lambda c: (0 if current_group_for[c] == grp else 1, -self.stable_steps.get(id(c), 0)))
                    for c in comps[cap:]:
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