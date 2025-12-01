from typing import Dict, List, Tuple, Any
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map from component id -> last assigned group name (by this controller)
        self.prev_assignments: Dict[int, str] = {}
        # Map from component id -> consecutive steps it has been in the same group
        self.stable_steps: Dict[int, int] = {}
        self.last_step = -1

    def _dist_to_field(self, loc, field) -> float:
        # Distance from point to nearest point in rectangle
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
        move_limit = N // 2  # default maximum drones we want to change each step

        # Build list of threatful fields
        threat_fields = [f for f in environment.fields if f.threat_level > 0]
        field_by_id = {f.id: f for f in environment.fields}

        # If none threatened -> idle all
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

        # Determine current group for each drone (prefer previous assignment if still valid)
        current_group_for: Dict[Any, str] = {}
        for comp in drones:
            key = id(comp)
            prev = self.prev_assignments.get(key)
            if prev in group_ids:
                current_group_for[comp] = prev
                continue
            # infer from component state/target_id
            tid = getattr(comp, 'target_id', None)
            if tid:
                name = f'protecting {tid}'
                if name in group_ids:
                    current_group_for[comp] = name
                else:
                    current_group_for[comp] = 'idle'
            else:
                current_group_for[comp] = 'idle'

        # Update stability counters based on current_group_for vs previous recorded assignment
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            prev = self.prev_assignments.get(key)
            if prev == curr:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0

        # Pick primary field (highest threat_level, tie-breaker by id)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = max(0, math.ceil(primary_field.drones_for_full_protection))

        # For every field compute required (ceil) and how many currently assigned (based on current_group_for)
        field_required = {}
        field_current_assigned = {}
        for f in threat_fields:
            name = f'protecting {f.id}'
            req = max(0, math.ceil(f.drones_for_full_protection))
            field_required[name] = req
            field_current_assigned[name] = 0
        for comp in drones:
            cg = current_group_for[comp]
            if cg in field_current_assigned:
                field_current_assigned[cg] += 1

        # Decide which fields to fully protect given drone budget.
        # Must include primary. For others use greedy value-per-cost = threat_level / extra_needed
        total_available = N
        selected_fields: List[str] = []
        # Start by selecting fields already fully protected and count them as selected, but primary must be selected regardless
        # We'll compute selected_fields as those we aim to fully protect.
        # Always include primary
        selected_fields.append(primary_group)
        assigned_needed = max(0, field_required[primary_group] - field_current_assigned.get(primary_group, 0))

        # Build candidate list excluding primary
        candidates = []
        for f in threat_fields:
            group = f'protecting {f.id}'
            if group == primary_group:
                continue
            extra_needed = max(0, field_required[group] - field_current_assigned.get(group, 0))
            # If already fully protected (extra_needed == 0), still consider it selected (we'll keep it)
            value = f.threat_level
            # If no extra needed, cost is 0 -> treat as high priority to keep
            candidates.append((group, value, extra_needed, f))

        # Greedy selection by value-per-cost, but treat zero-cost fields first
        zero_cost = [c for c in candidates if c[2] == 0]
        for group, _, _, _ in zero_cost:
            selected_fields.append(group)
        # Now remaining with positive cost
        pos_cost = [c for c in candidates if c[2] > 0]
        # Compute value per cost; if cost is big and value small, deprioritize
        pos_cost.sort(key=lambda item: (-(item[1] / item[2]), -item[1]))  # best ratio first
        # Greedily add while we have drones
        current_assigned_total = 0
        # count current assignments that we'll keep for selected fields (we'll keep existing protectors)
        for group in selected_fields:
            current_assigned_total += min(field_current_assigned.get(group, 0), field_required.get(group, 0))
        # now consider pos_cost
        for group, value, extra_needed, f in pos_cost:
            # if we can afford extra_needed with remaining drones, select
            # remaining drones considered as N - current_assigned_total
            remaining_budget = N - current_assigned_total
            if extra_needed <= remaining_budget:
                selected_fields.append(group)
                current_assigned_total += extra_needed
            # otherwise skip (we prefer fully protecting fewer fields)
        # After selection, recompute required_to_assign per selected field
        to_assign_needed: Dict[str, int] = {}
        for group in selected_fields:
            req = field_required.get(group, 0)
            cur = field_current_assigned.get(group, 0)
            need = max(0, req - cur)
            to_assign_needed[group] = need

        # Ensure primary will be fully protected: if it's not achievable with move_limit constraint, we will allow overriding move_limit.
        # We now choose drones for each selected field preferring minimal churn and close distance.

        # Helper: for each drone compute qualities for a given field
        # We'll prepare pools and choose drones per field
        unallocated = set(drones)
        desired: Dict[int, str] = {}

        # Prepare index lists by current_group_for and state to prefer keepers
        drones_by_group: Dict[str, List[Any]] = defaultdict(list)
        for comp in drones:
            drones_by_group[current_group_for[comp]].append(comp)

        # For deterministic choices, we sort drones by stable_steps descending so longer-stable are preferred to keep
        def sort_keep_priority(lst: List[Any], reverse_distance_field=None):
            # Prefer those already in the group (higher stability), and closer to reverse_distance_field if provided.
            def key(comp):
                k = self.stable_steps.get(id(comp), 0)
                # we want descending stability (bigger first) so use -k as first sort key for ascending sort
                primary = -k
                if reverse_distance_field is not None:
                    d = self._dist_to_field(comp.location, reverse_distance_field)
                else:
                    d = 0.0
                # also prefer those already protecting (we call this outside)
                return (primary, d)
            return sorted(lst, key=key)

        # Utility to pick candidates for a field: preference order described in improvements
        def pick_for_field(field_obj, group_name, need, allow_steal_from_other=False):
            picked = []
            if need <= 0:
                return picked
            # 1) already protecting this field
            current_props = [c for c in drones_by_group.get(group_name, []) if c in unallocated]
            current_props_sorted = sort_keep_priority(current_props, reverse_distance_field=field_obj)
            for c in current_props_sorted:
                if len(picked) >= need:
                    break
                picked.append(c)
                unallocated.discard(c)
            if len(picked) >= need:
                return picked
            # 2) drones moving_to_field with target this field
            movers = []
            for c in list(unallocated):
                if getattr(c, 'state', '') == 'moving_to_field' and getattr(c, 'target_id', None) == field_obj.id:
                    movers.append(c)
            movers_sorted = sort_keep_priority(movers, reverse_distance_field=field_obj)
            for c in movers_sorted:
                if len(picked) >= need:
                    break
                picked.append(c)
                unallocated.discard(c)
            if len(picked) >= need:
                return picked
            # 3) idle drones
            idles = [c for c in list(unallocated) if current_group_for[c] == 'idle']
            idles_sorted = sorted(idles, key=lambda comp: self._dist_to_field(comp.location, field_obj))
            for c in idles_sorted:
                if len(picked) >= need:
                    break
                picked.append(c)
                unallocated.discard(c)
            if len(picked) >= need:
                return picked
            # 4) steal from other fields but prefer low stability and far distance
            # Only if allow_steal_from_other True (we'll set it for primary to ensure it's fully protected)
            if allow_steal_from_other:
                # candidates: drones that are protecting other fields (not yet allocated)
                other_protectors = [c for c in list(unallocated) if current_group_for[c].startswith('protecting ')]
                # sort by (low stability, large distance to their current field, close to target field)
                def steal_key(comp):
                    stab = self.stable_steps.get(id(comp), 0)
                    # distance to the target field
                    d_to_target = self._dist_to_field(comp.location, field_obj)
                    return (stab, d_to_target)
                other_protectors_sorted = sorted(other_protectors, key=steal_key)
                for c in other_protectors_sorted:
                    if len(picked) >= need:
                        break
                    picked.append(c)
                    unallocated.discard(c)
            # 5) fallback: any remaining drones by proximity
            if len(picked) < need:
                rest = sorted(list(unallocated), key=lambda comp: self._dist_to_field(comp.location, field_obj))
                for c in rest:
                    if len(picked) >= need:
                        break
                    picked.append(c)
                    unallocated.discard(c)
            return picked

        # First ensure primary is fully protected (allow stealing)
        primary_field_obj = primary_field
        primary_need = to_assign_needed.get(primary_group, 0)
        primary_picked = pick_for_field(primary_field_obj, primary_group, primary_need, allow_steal_from_other=True)
        for c in primary_picked:
            desired[id(c)] = primary_group

        # Then for other selected fields, pick without heavy stealing (prefer not to disrupt)
        for group in selected_fields:
            if group == primary_group:
                continue
            # find associated field object
            fid = group.replace('protecting ', '')
            field_obj = field_by_id.get(fid)
            if field_obj is None:
                continue
            need = to_assign_needed.get(group, 0)
            # For secondary fields, do not allow stealing from other fields; only take idle/movers and already-there
            picked = pick_for_field(field_obj, group, need, allow_steal_from_other=False)
            for c in picked:
                desired[id(c)] = group

        # At this point, some drones remain unallocated. They should either remain in their current groups (prefer) or be set to idle.
        for comp in list(unallocated):
            # Prefer to keep current assignment if it's a protecting group and not causing overprotection
            curr_group = current_group_for[comp]
            if curr_group.startswith('protecting ') and curr_group in selected_fields:
                # If the selected field already has enough assigned (we kept earlier protectors but may have fewer),
                # keeping them won't overprotect because we ensured no overprotection for selected_fields.
                desired[id(comp)] = curr_group
            else:
                # Idle by default
                desired[id(comp)] = 'idle'

        # Count how many would change
        would_change = []
        would_keep = []
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            targ = desired.get(key, 'idle')
            # Ensure targ exists in group_ids; if not, fallback to idle
            if targ not in group_ids:
                targ = 'idle'
                desired[key] = 'idle'
            if targ != curr:
                would_change.append((comp, curr, targ))
            else:
                would_keep.append((comp, curr, targ))

        # Enforce move_limit but ensure primary gets all needed moves
        # Count how many of the primary assignments require change
        primary_changes = [w for w in would_change if w[2] == primary_group]
        non_primary_changes = [w for w in would_change if w[2] != primary_group]

        final_assignment: Dict[int, str] = {}

        # Always allow moves sufficient to make primary fully protected (even if exceeds move_limit)
        needed_primary_moves = len(primary_changes)
        allowed_moves = move_limit
        if needed_primary_moves > allowed_moves:
            # increase allowed_moves to accommodate primary, but cap at N
            allowed_moves = min(N, needed_primary_moves)

        # If allowed_moves still less than primary moves (shouldn't happen), force primary moves
        # Build list of change candidates prioritized to change: low stability, not currently protecting high-stability fields
        def change_priority(item):
            comp, curr, targ = item
            key = id(comp)
            stab = self.stable_steps.get(key, 0)
            # Prefer to change drones with lower stability (smaller stab), and those not currently protecting (curr == 'idle') are easier to change
            currently_protecting = 1 if curr.startswith('protecting ') else 0
            # we want small stab first, then not currently_protecting first
            return (stab, currently_protecting, self._dist_to_field(comp.location, primary_field_obj))

        # Build list of candidates sorted by priority
        change_candidates = sorted(would_change, key=change_priority)

        # Select up to allowed_moves candidates to change, but ensure we include all primary_changes
        to_change_set = set()
        # include all primary changes first
        for comp, curr, targ in primary_changes:
            to_change_set.add(id(comp))
        # fill remaining allowed slots with best non-primary changes
        for comp, curr, targ in change_candidates:
            if len(to_change_set) >= allowed_moves:
                break
            key = id(comp)
            if key in to_change_set:
                continue
            to_change_set.add(key)

        # Now assign final: changed ones get desired targ, others keep current
        for comp, curr, targ in would_change:
            key = id(comp)
            if key in to_change_set:
                final_assignment[key] = targ
            else:
                # keep current (ensure it's valid)
                final_assignment[key] = curr if curr in group_ids else 'idle'
        for comp, curr, targ in would_keep:
            final_assignment[id(comp)] = curr

        # Sanity: ensure selected_fields are fully protected in final_assignment; if not, try to force additional swaps (should rarely be needed)
        # Compute final counts
        final_counts = defaultdict(int)
        for comp in drones:
            grp = final_assignment.get(id(comp), 'idle')
            final_counts[grp] += 1
        # For any selected field lacking protectors, try to reassign extra idles or least stable protectors
        for group in selected_fields:
            need_total = field_required.get(group, 0)
            curr_assigned = final_counts.get(group, 0)
            if curr_assigned >= need_total:
                continue
            need_more = need_total - curr_assigned
            # find candidates we can flip: those currently idle or in non-selected protecting groups, sorted by priority
            candidates = []
            for comp in drones:
                key = id(comp)
                if final_assignment[key] == group:
                    continue
                if final_assignment[key] == 'idle' or (final_assignment[key].startswith('protecting ') and final_assignment[key] not in selected_fields):
                    candidates.append(comp)
            # sort by preference: low stability first and close to target field
            fid = group.replace('protecting ', '')
            field_obj = field_by_id.get(fid)
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), self._dist_to_field(c.location, field_obj)))
            for c in candidates[:need_more]:
                final_assignment[id(c)] = group
                final_counts[group] += 1

        # Ensure at least half_min drones are protecting something; if not, add closest drones to primary
        protecting_count = sum(1 for grp in final_assignment.values() if grp.startswith('protecting '))
        if protecting_count < half_min:
            need_more = half_min - protecting_count
            # find drones not protecting currently, sorted by distance to primary
            candidates = [comp for comp in drones if not final_assignment[id(comp)].startswith('protecting ')]
            candidates.sort(key=lambda c: self._dist_to_field(c.location, primary_field_obj))
            for c in candidates[:need_more]:
                final_assignment[id(c)] = primary_group

        # Final pass: ensure no field is overprotected (cap at required)
        assigned_per_field = defaultdict(list)
        for comp in drones:
            grp = final_assignment.get(id(comp), 'idle')
            if grp.startswith('protecting '):
                assigned_per_field[grp].append(comp)
        for grp, comps in assigned_per_field.items():
            cap = field_required.get(grp, 0)
            if len(comps) > cap:
                # drop excess comps: choose to keep those with highest stability and/or already were protecting
                def keep_key(comp):
                    key = id(comp)
                    # prefer those that were already protecting this group
                    was_here = 1 if current_group_for[comp] == grp else 0
                    stab = self.stable_steps.get(key, 0)
                    return (-was_here, -stab)  # sort descending prefer was_here and higher stability
                comps_sorted = sorted(comps, key=keep_key)
                # keep first cap, set others to idle
                keep = set(id(c) for c in comps_sorted[:cap])
                for c in comps_sorted[cap:]:
                    final_assignment[id(c)] = 'idle'

        # Apply assignments
        for comp in drones:
            key = id(comp)
            group = final_assignment.get(key, 'idle')
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