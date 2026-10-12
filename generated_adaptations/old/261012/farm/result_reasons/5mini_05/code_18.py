from typing import Dict, Any, List, Set
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

        # Gather threatful fields whose protecting groups exist
        threat_fields = [f for f in environment.fields if f.threat_level > 0 and f'protecting {f.id}' in group_ids]
        field_by_group = {f'protecting {f.id}': f for f in threat_fields}

        # If no threats, idle all
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

        # Infer current group for each drone (prefer our previous assignment if valid)
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

        # Primary field selection
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = min(required_map.get(primary_group, 0), N)

        # arrival time helper
        def arrival_time(comp, field):
            return self._dist_to_field(comp.location, field) / self.DRONE_SPEED

        # Helper: choose k drones with smallest arrival times to field, preferring keepers/movers to reduce churn.
        def best_k_by_arrival(field, k, allow_from_locked=False):
            entries = []
            for comp in drones:
                key = id(comp)
                # if not allowed to take from locked and this drone is locked and not in target field, skip
                if not allow_from_locked and key in locked_drones and current_group_for[comp] != f'protecting {field.id}':
                    continue
                arr = arrival_time(comp, field)
                # prefer keepers and movers
                is_keeper = 0 if current_group_for[comp] == f'protecting {field.id}' else 1
                is_mover = 0 if (getattr(comp, 'state', '') == 'moving_to_field' and getattr(comp, 'target_id', None) == field.id) else 1
                stab = self.stable_steps.get(key, 0)
                # sort by (arrival, keeper, mover, stability)
                entries.append((arr, is_keeper, is_mover, stab, key, comp))
            entries.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
            return [e[5] for e in entries[:k]]

        # Desired mapping and an available pool of drones (not locked)
        desired: Dict[int, str] = {}
        available_set = set(comp for comp in drones if id(comp) not in locked_drones)

        # Assign locked drones first (they remain where they are)
        for comp in drones:
            key = id(comp)
            if key in locked_drones:
                desired[key] = current_group_for[comp]

        # Primary assignment: pick k drones minimizing arrival (prefer keepers/movers). Allow stealing from unlocked donors.
        if primary_group in locked_fields:
            # primary already locked: keep its drones assigned
            for comp in drones:
                if current_group_for[comp] == primary_group:
                    desired[id(comp)] = primary_group
                    if comp in available_set:
                        available_set.discard(comp)
        else:
            primary_candidates = best_k_by_arrival(primary_field, required_primary, allow_from_locked=False)
            # If not enough candidates (rare), allow taking from locked as last resort
            if len(primary_candidates) < required_primary:
                primary_candidates = best_k_by_arrival(primary_field, required_primary, allow_from_locked=True)
            # assign selected
            for comp in primary_candidates[:required_primary]:
                desired[id(comp)] = primary_group
                if comp in available_set:
                    available_set.discard(comp)

        # Greedily attempt to fully protect other fields by descending threat per cost (threat / k)
        other_fields = [f for f in threat_fields if f.id != primary_field.id]
        other_fields.sort(key=lambda f: (f.threat_level / max(1.0, max(1, math.ceil(f.drones_for_full_protection)))), reverse=True)

        for f in other_fields:
            grp = f'protecting {f.id}'
            if grp in locked_fields:
                # keep locked drones
                for comp in drones:
                    if current_group_for[comp] == grp:
                        desired[id(comp)] = grp
                        if comp in available_set:
                            available_set.discard(comp)
                continue
            k = required_map.get(grp, 0)
            if k <= 0:
                continue
            # Count how many already assigned/planned
            already_planned = sum(1 for comp in drones if desired.get(id(comp), current_group_for[comp]) == grp)
            need = max(0, k - already_planned)
            if need <= 0:
                continue
            # Build candidate pool for this field: prefer available_set + keepers
            # We'll pick best k by arrival but ensure we don't take locked donors
            candidates = best_k_by_arrival(f, need, allow_from_locked=False)
            # If not enough from available, try allowing locked drones only if they are keepers (they would have been filtered already)
            if len(candidates) < need:
                candidates = best_k_by_arrival(f, need, allow_from_locked=True)
            # Assign those from candidates which are available or already keepers
            assigned = 0
            for comp in candidates:
                if assigned >= need:
                    break
                key = id(comp)
                # If comp is locked and not keeper skip (shouldn't happen due to allow flag)
                if key in locked_drones and current_group_for[comp] != grp:
                    continue
                # If comp already desired elsewhere (shouldn't), skip
                if id(comp) in desired and desired[id(comp)] != grp:
                    continue
                desired[id(comp)] = grp
                if comp in available_set:
                    available_set.discard(comp)
                assigned += 1

        # After trying full protections, preposition remaining drones:
        # For each remaining available drone, assign it to the threatened field where (arrival / threat) is minimal
        # (i.e., near high-threat fields).
        remaining = [comp for comp in drones if id(comp) not in desired]
        # compute for each drone the best field to preposition to
        for comp in remaining:
            best_field = None
            best_score = float('inf')
            for f in threat_fields:
                grp = f'protecting {f.id}'
                # skip fields that are already full-protected and locked
                # but allow prepositioning near them if desired (we'll prefer not to steal locked drones)
                if required_map.get(grp, 0) == 0:
                    continue
                arr = arrival_time(comp, f)
                # score: arrival / (threat + small_eps) -> smaller is better
                score = arr / max(0.001, f.threat_level)
                if score < best_score:
                    best_score = score
                    best_field = f
            if best_field is not None:
                desired[id(comp)] = f'protecting {best_field.id}'
            else:
                desired[id(comp)] = 'idle'

        # Cap assignments to no overprotection: if any group exceeds its required_map cap, trim worst-assigned drones
        assigned_by_group = defaultdict(list)
        for comp in drones:
            grp = desired.get(id(comp), current_group_for[comp])
            assigned_by_group[grp].append(comp)
        for grp, comps in assigned_by_group.items():
            if grp.startswith('protecting ') and grp in required_map:
                cap = required_map[grp]
                if len(comps) > cap:
                    # sort to keep those already in grp and with high stability
                    comps.sort(key=lambda c: (0 if current_group_for[c] == grp else 1, -self.stable_steps.get(id(c), 0)))
                    keep = comps[:cap]
                    drop = comps[cap:]
                    for c in drop:
                        desired[id(c)] = 'idle'

        # Now enforce churn limit: allow primary-related changes, and pick other changes up to change_limit
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

        # Allow all changes that assign into primary_field (critical), then choose additional changes up to change_limit
        critical = [c for c in would_change if c[2] == primary_group]
        non_critical = [c for c in would_change if c[2] != primary_group]

        final_assignment: Dict[int, str] = {id(comp): current_group_for[comp] for comp in drones}
        # apply critical changes
        for comp, curr, targ in critical:
            final_assignment[id(comp)] = targ

        used = len(critical)
        remaining_slots = max(0, change_limit - used)

        # Choose non-critical changes to allow: prefer low stability, currently idle/moving to reduce disruption
        def noncrit_key(item):
            comp, curr, targ = item
            key = id(comp)
            stab = self.stable_steps.get(key, 0)
            protecting_now = 1 if curr.startswith('protecting ') else 0
            # distance to target may be considered (closer better)
            dist = 0.0
            if targ.startswith('protecting '):
                fid = targ.replace('protecting ', '')
                fobj = next((ff for ff in threat_fields if ff.id == fid), None)
                if fobj is not None:
                    dist = self._dist_to_field(comp.location, fobj)
            return (stab, protecting_now, dist, key % 997)
        non_critical.sort(key=noncrit_key)
        allowed_noncrit = non_critical[:remaining_slots]
        allowed_ids = set(id(item[0]) for item in allowed_noncrit)

        for comp, curr, targ in non_critical:
            if id(comp) in allowed_ids:
                final_assignment[id(comp)] = targ
            else:
                final_assignment[id(comp)] = curr if curr in group_ids else 'idle'

        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # Ensure primary fully protected in final_assignment; if not, force overrides (primary rule)
        final_primary_count = sum(1 for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) == primary_group)
        if final_primary_count < required_primary:
            need = required_primary - final_primary_count
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), arrival_time(c, primary_field)))
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group

        # Final cap enforcement again
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

        # Apply assignments and update prev/stability
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