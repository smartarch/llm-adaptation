from typing import Dict, Any, List
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0  # given in the problem

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map drone id -> last assigned group (by this controller)
        self.prev_assignments: Dict[int, str] = {}
        # Map drone id -> consecutive steps in same group
        self.stable_steps: Dict[int, int] = {}
        self.last_step = -1

    def _dist_to_field(self, loc, field) -> float:
        # Distance from point to nearest point inside rectangle
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
        move_limit = N // 2  # prefer not to change more than half of drones per step

        # Build list of fields with threat > 0
        threat_fields = [f for f in environment.fields if f.threat_level > 0 and f'protecting {f.id}' in group_ids]
        field_by_group = {f'protecting {f.id}': f for f in threat_fields}

        # If no threats, idle everyone
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
                continue
            # else infer from state/target
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

        # Select primary field (highest threat; tie by id)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = max(0, math.ceil(primary_field.drones_for_full_protection))
        required_primary = min(required_primary, N)

        # Precompute arrival times for all drones to each field lazily as needed.
        # For primary: pick the closest drones by arrival_time = distance / speed.
        drone_arrival = []
        for comp in drones:
            d = self._dist_to_field(comp.location, primary_field)
            arrival = d / self.DRONE_SPEED
            # tie-breaker: prefer drones already protecting primary (reduce churn)
            already_primary = 1 if current_group_for[comp] == primary_group else 0
            # we'll sort by (arrival, -already_primary)
            drone_arrival.append((arrival, -already_primary, comp))
        drone_arrival.sort(key=lambda x: (x[0], x[1]))

        desired: Dict[int, str] = {}
        unassigned = set(drones)

        # Assign primary: take top required_primary drones (closest arrival)
        primary_selected = [t[2] for t in drone_arrival[:required_primary]]
        for comp in primary_selected:
            desired[id(comp)] = primary_group
            if comp in unassigned:
                unassigned.remove(comp)

        # Helper: count how many will be assigned to group after current desired mapping (including keeping current)
        def planned_count(group_name: str) -> int:
            cnt = sum(1 for k, g in desired.items() if g == group_name)
            for comp in drones:
                if id(comp) in desired:
                    continue
                if current_group_for[comp] == group_name:
                    cnt += 1
            return cnt

        # Secondary: greedily fill other fields by threat descending using closest available drones
        other_fields = sorted([f for f in threat_fields if f.id != primary_field.id],
                              key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        # precompute required map
        required_map = {f'protecting {f.id}': max(0, math.ceil(f.drones_for_full_protection)) for f in threat_fields}
        # For each secondary field, attempt to fill to required capacity using closest unassigned drones.
        for field in other_fields:
            group = f'protecting {field.id}'
            req = required_map.get(group, 0)
            cur_planned = planned_count(group)
            need = max(0, req - cur_planned)
            if need <= 0:
                continue
            # rank unassigned drones by arrival time to this field (prefer those already in that group lightly)
            ranked = []
            for comp in list(unassigned):
                dist = self._dist_to_field(comp.location, field)
                arrival = dist / self.DRONE_SPEED
                already = 1 if current_group_for[comp] == group else 0
                ranked.append((arrival, -already, comp))
            ranked.sort(key=lambda x: (x[0], x[1]))
            for item in ranked[:need]:
                comp = item[2]
                desired[id(comp)] = group
                if comp in unassigned:
                    unassigned.remove(comp)

        # After filling full protections, ensure at least half_min drones are used for protection if capacity allows.
        protecting_count = sum(1 for g in desired.values() if g.startswith('protecting '))
        # plus those currently protecting and not re-assigned elsewhere
        protecting_count += sum(1 for comp in drones if id(comp) not in desired and current_group_for[comp].startswith('protecting '))
        if protecting_count < half_min:
            needed_more = half_min - protecting_count
            # compute remaining capacities per field (cap = required - planned_count)
            capacities = []
            assigned_counts = {}
            for f in threat_fields:
                g = f'protecting {f.id}'
                assigned_counts[g] = planned_count(g)
            for f in threat_fields:
                g = f'protecting {f.id}'
                cap = max(0, required_map.get(g, 0) - assigned_counts.get(g, 0))
                if cap > 0:
                    capacities.append((f, g, cap))
            # sort capacities by threat descending
            capacities.sort(key=lambda x: x[0].threat_level, reverse=True)
            for field, group, cap in capacities:
                if needed_more <= 0:
                    break
                # pick closest unassigned up to cap
                ranked = []
                for comp in list(unassigned):
                    dist = self._dist_to_field(comp.location, field)
                    arrival = dist / self.DRONE_SPEED
                    ranked.append((arrival, comp))
                ranked.sort(key=lambda x: x[0])
                take = min(cap, needed_more)
                for _, comp in ranked[:take]:
                    desired[id(comp)] = group
                    if comp in unassigned:
                        unassigned.remove(comp)
                    needed_more -= 1
                    if needed_more <= 0:
                        break
            # If still needed_more > 0 (no capacity left), allow partial assignments to highest-threat fields:
            if needed_more > 0:
                # choose highest threat fields and assign remaining unassigned drones by their proximity (partial protection to reach half)
                fields_by_threat = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
                remaining_list = list(unassigned)
                # sort remaining drones by distance to primary (prefer close to primary) or better: to fields by threat
                for field in fields_by_threat:
                    if needed_more <= 0:
                        break
                    ranked = sorted(remaining_list, key=lambda c: self._dist_to_field(c.location, field))
                    for comp in ranked:
                        if needed_more <= 0:
                            break
                        desired[id(comp)] = f'protecting {field.id}'
                        if comp in unassigned:
                            unassigned.remove(comp)
                        needed_more -= 1
                    remaining_list = list(unassigned)

        # Any remaining unassigned: prefer to keep current protecting assignment if valid and not over cap; otherwise idle
        assigned_counts = {}
        for comp in drones:
            grp = desired.get(id(comp), current_group_for[comp])
            assigned_counts[grp] = assigned_counts.get(grp, 0) + 1
        for comp in list(unassigned):
            curr = current_group_for[comp]
            assign = None
            if curr.startswith('protecting '):
                cap = required_map.get(curr, 0)
                if assigned_counts.get(curr, 0) < cap:
                    assign = curr
            if assign is None:
                assign = 'idle'
            desired[id(comp)] = assign
            assigned_counts[assign] = assigned_counts.get(assign, 0) + 1
            unassigned.remove(comp)

        # Ensure no overprotection: trim low-priority drones from groups exceeding caps
        for group, cap in required_map.items():
            assigned_list = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) == group]
            if len(assigned_list) <= cap:
                continue
            # Sort by keep-priority: prefer those already in that group and higher stability
            def keep_key(c):
                k = id(c)
                was_here = 1 if current_group_for[c] == group else 0
                stab = self.stable_steps.get(k, 0)
                # higher was_here and higher stability should be kept (so sort descending)
                return (-was_here, -stab, self._dist_to_field(c.location, field_by_group.get(group, primary_field)))
            assigned_list.sort(key=keep_key)
            keep = assigned_list[:cap]
            drop = assigned_list[cap:]
            for c in drop:
                desired[id(c)] = 'idle'

        # Now enforce move_limit but allow override for primary if necessary.
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

        # Ensure all assignments needed for primary are applied (critical)
        critical_changes = [c for c in would_change if c[2] == primary_group]
        non_critical_changes = [c for c in would_change if c[2] != primary_group]

        # Determine allowed non-critical changes
        # Must at least allow critical changes; reduce non-critical if necessary to meet move_limit
        required_changes_for_primary = len(critical_changes)
        # If required_changes_for_primary > move_limit, override limit to allow primary (primary rule strict)
        allowed_non_critical = max(0, move_limit - required_changes_for_primary) if required_changes_for_primary <= move_limit else len(non_critical_changes)

        # Pick which non-critical changes to allow: prefer to move drones with low stability and those currently idle/moving (not protecting)
        def noncrit_priority(item):
            comp, curr, targ = item
            k = id(comp)
            stab = self.stable_steps.get(k, 0)
            protecting_now = 1 if curr.startswith('protecting ') else 0
            # smaller stab first, not-protecting preferred to move
            return (stab, protecting_now, self._dist_to_field(comp.location, field_by_group.get(targ, primary_field)))

        non_critical_changes.sort(key=noncrit_priority)
        allowed_noncrit_set = set(id(c[0]) for c in non_critical_changes[:allowed_non_critical])

        final_assignment: Dict[int, str] = {}
        # Apply all critical changes
        for comp, curr, targ in critical_changes:
            final_assignment[id(comp)] = targ
        # Apply allowed non-critical changes
        for comp, curr, targ in non_critical_changes:
            if id(comp) in allowed_noncrit_set:
                final_assignment[id(comp)] = targ
            else:
                # keep current
                final_assignment[id(comp)] = curr if curr in group_ids else 'idle'
        # Keep unchanged ones
        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # Sanity: ensure primary is fully protected in final_assignment; if not, force additional moves (override)
        final_counts = defaultdict(int)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_counts[grp] += 1
        if final_counts.get(primary_group, 0) < required_primary:
            need = required_primary - final_counts.get(primary_group, 0)
            # pick candidates not currently primary, sorted by arrival to primary and low stability
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), self._dist_to_field(c.location, primary_field)))
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group

        # Final cap enforcement (again) to ensure no overprotection after forced moves
        final_group_counts = defaultdict(list)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_group_counts[grp].append(comp)
        for group, comps in final_group_counts.items():
            if group.startswith('protecting ') and group in required_map:
                cap = required_map[group]
                if len(comps) > cap:
                    # keep best
                    comps.sort(key=lambda comp: (-1 if current_group_for[comp] == group else 0, -self.stable_steps.get(id(comp), 0)))
                    keep = comps[:cap]
                    drop = comps[cap:]
                    for c in drop:
                        final_assignment[id(c)] = 'idle'

        # Apply assignments through environment.assign_group and update prev/stability
        for comp in drones:
            key = id(comp)
            group = final_assignment.get(key, current_group_for[comp])
            if group not in group_ids:
                group = 'idle'
            environment.assign_group(comp, group)
            prev = self.prev_assignments.get(key)
            if prev == group:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0
            self.prev_assignments[key] = group

        self.last_step = step