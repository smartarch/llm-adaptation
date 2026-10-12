Reasoning and improved strategy

Problems observed earlier
- Too much complexity in stealing and stability logic caused wrong drones to move or prevented urgent moves to the primary field.
- Over/under assignment due to rounding choices and overly-strict movement limits increased damage.
- The controller must always fully protect the highest-threat field ASAP even if that requires many moves; other stability constraints are secondary.

Goals for the improved strategy
- Always fully protect the primary (highest-threat) field using the closest available drones (minimize arrival time).
- Prefer to keep drones that are already protecting a field (stability), but not at the cost of leaving the primary unprotected.
- Do not overprotect (never assign more than drones_for_full_protection to a field).
- Try to fully protect additional high-threat fields only if enough drones remain.
- Ensure at least half of drones are assigned to some protecting group if the fields' capacities allow it (use any remaining field capacity before giving up).
- Limit churn where possible: avoid changing more than half the fleet in a step except when necessary to protect the primary field.

High-level algorithm
1. If no field has threat > 0, put all drones to "idle".
2. Identify primary field (max threat_level). Compute required drones (ceil).
3. Select drones for the primary: keep those already protecting primary and those already moving to it; then take idle drones and lastly other drones ordered by low stability and distance. Allow overriding the usual move-limit to guarantee primary protection.
4. For remaining drones, iterate other fields in descending threat; for each, fill up to their required count using similar preference (already there, movers, idle, then low-stability protectors).
5. After filling full protections, if protecting-count < half of fleet, try to use remaining capacity of fields (their remaining requirements) to increase protecting-count up to half. Only if no capacity left, leave drones idle (do not overprotect).
6. Compute which drones would change group. Enforce change-limit (<= floor(N/2)) except allow extra moves if necessary to secure the primary. Choose which non-essential drones to keep in place based on stability.
7. Apply assignments with environment.assign_group, update internal tracking.

This approach is simpler, enforces the must-have primary protection, avoids overprotection, uses field capacity to meet the half-usage constraint when possible, and biases toward stability without blocking the primary requirement.

Code

```py
from typing import Dict, Any, List
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track previous assignments and stability (consecutive steps in same group)
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
        change_limit = N // 2  # prefer not to change more than half in one step

        # Build list of fields with threat > 0 that have protecting groups valid in group_ids
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

        # Determine current group inference for each drone (prefer prev assignment if it exists and is still valid)
        current_group_for: Dict[Any, str] = {}
        for comp in drones:
            key = id(comp)
            prev = self.prev_assignments.get(key)
            if prev in group_ids:
                current_group_for[comp] = prev
                continue
            # infer from state/target
            tid = getattr(comp, 'target_id', None)
            if tid:
                grp = f'protecting {tid}'
                current_group_for[comp] = grp if grp in group_ids else 'idle'
            else:
                current_group_for[comp] = 'idle'

        # Update stability counters (based on whether current_group equals previously recorded)
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            prev = self.prev_assignments.get(key)
            if prev == curr:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0

        # Choose primary field (highest threat, tie-breaker by id)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = max(0, math.ceil(primary_field.drones_for_full_protection))

        # Compute current counts per protecting group (based on current_group_for)
        current_counts = defaultdict(int)
        for comp in drones:
            cg = current_group_for[comp]
            if cg.startswith('protecting '):
                current_counts[cg] += 1

        # Helper: sort drones by preferred order for assignment to a particular field:
        # 1) already protecting that field (high stability)
        # 2) moving_to_field with that target
        # 3) idle (closest first)
        # 4) protecting other fields but with low stability and close distance
        def rank_candidates_for_field(field_obj, group_name, candidates):
            scored = []
            for comp in candidates:
                key = id(comp)
                score = 0
                # prefer already in group
                if current_group_for[comp] == group_name:
                    score -= 10000  # very high priority (lower score better)
                # prefer moving to that field
                if getattr(comp, 'state', '') == 'moving_to_field' and getattr(comp, 'target_id', None) == field_obj.id:
                    score -= 5000
                # proximity helps
                dist = self._dist_to_field(comp.location, field_obj)
                score += dist
                # penalize high stability (we like to keep stable ones where they are; so we don't want to move them away)
                # but for choosing who to assign to this field, we prefer those with higher stability if they are already here (handled above)
                # for others, prefer lower stable (more willing to move)
                stab = self.stable_steps.get(key, 0)
                score += stab * 1.0
                scored.append((score, comp))
            scored.sort(key=lambda x: x[0])
            return [c for _, c in scored]

        # Build pool of unassigned drones (initially all)
        unassigned = set(drones)
        desired: Dict[int, str] = {}

        # Step A: ensure primary is fully protected. Select closest / best candidates until required_primary reached.
        primary_candidates = list(drones)
        primary_ranked = rank_candidates_for_field(primary_field, primary_group, primary_candidates)
        # Count how many already effectively assigned to primary (we'll keep them)
        already_primary = [c for c in drones if current_group_for[c] == primary_group]
        for c in already_primary:
            if len(already_primary) > required_primary:
                # If more currently there than needed (overprotection), we'll trim later. For now keep them flagged.
                break
        # Pick up to required_primary from ranked list, but prefer to keep those already there
        selected_primary = []
        for c in primary_ranked:
            if len(selected_primary) >= required_primary:
                break
            selected_primary.append(c)
        # Mark selected_primary desired group
        for c in selected_primary:
            desired[id(c)] = primary_group
            if c in unassigned:
                unassigned.remove(c)

        # Step B: Fill other fields greedily by threat descending, up to their required capacities (no overprotection).
        other_fields = sorted([f for f in threat_fields if f.id != primary_field.id], key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        # compute required per field (ceil) and how many already currently there
        required_map = {}
        for f in threat_fields:
            required_map[f'protecting {f.id}'] = max(0, math.ceil(f.drones_for_full_protection))
        # For each other field try to fill its deficit using unassigned pool
        for field in other_fields:
            group = f'protecting {field.id}'
            needed = required_map[group] - sum(1 for comp in drones if desired.get(id(comp), current_group_for[comp]) == group)
            if needed <= 0:
                continue
            # rank unassigned candidates for this field
            ranked = rank_candidates_for_field(field, group, list(unassigned))
            # pick up to needed
            picked = ranked[:needed]
            for c in picked:
                desired[id(c)] = group
                if c in unassigned:
                    unassigned.remove(c)

        # Step C: After filling full protections, if fewer than half protecting, use remaining field capacity to reach half_min
        protecting_count = sum(1 for gid in desired.values() if gid.startswith('protecting ')) + \
                           sum(1 for comp in drones if id(comp) not in desired and current_group_for[comp].startswith('protecting '))
        # protecting_count counts both newly desired and those we kept in place (current_group_for)
        if protecting_count < half_min:
            need_more = half_min - protecting_count
            # find fields that still have capacity (required - assigned)
            capacity_list = []
            # compute assigned counts including desired
            assigned_counts = defaultdict(int)
            for comp in drones:
                gid = desired.get(id(comp), current_group_for[comp])
                if gid.startswith('protecting '):
                    assigned_counts[gid] += 1
            for f in threat_fields:
                g = f'protecting {f.id}'
                cap = required_map.get(g, 0) - assigned_counts.get(g, 0)
                if cap > 0:
                    capacity_list.append((f, g, cap))
            # Sort capacity_list by threat descending
            capacity_list.sort(key=lambda x: x[0].threat_level, reverse=True)
            for field, group, cap in capacity_list:
                if need_more <= 0:
                    break
                # pick up to cap from unassigned, ranked by proximity
                ranked = rank_candidates_for_field(field, group, list(unassigned))
                pick = ranked[:min(cap, need_more)]
                for c in pick:
                    desired[id(c)] = group
                    if c in unassigned:
                        unassigned.remove(c)
                    need_more -= 1
                if need_more <= 0:
                    break
            # If still need_more but no capacity left, we cannot overprotect by spec; leave remaining drones as is (idle or current)
            # This may mean half_min is unattainable; we do not overprotect to meet it.

        # Step D: Any still unassigned -> prefer keep their current group if it's a protecting group and not overcap, else idle
        # First compute desired assigned counts per group
        assigned_counts = defaultdict(int)
        for comp in drones:
            gid = desired.get(id(comp), current_group_for[comp])
            assigned_counts[gid] += 1
        # assign leftover respecting caps
        for comp in list(unassigned):
            curr = current_group_for[comp]
            assign = None
            if curr.startswith('protecting '):
                cap = required_map.get(curr, 0)
                if assigned_counts[curr] < cap:
                    assign = curr
            if assign is None:
                assign = 'idle'
            desired[id(comp)] = assign
            assigned_counts[assign] += 1
            unassigned.remove(comp)

        # Ensure no overprotection: if any group exceeds its cap, trim lowest-priority drones (those not originally there and with low stability)
        for group, cap in required_map.items():
            if assigned_counts.get(group, 0) <= cap:
                continue
            # find drones assigned to this group
            assigned_list = [comp for comp in drones if desired.get(id(comp), current_group_for[comp]) == group]
            # Sort by priority to keep: those already in that group and high stability first
            def keep_key(comp):
                key = id(comp)
                was_here = 1 if current_group_for[comp] == group else 0
                stab = self.stable_steps.get(key, 0)
                # higher was_here and higher stability should be kept, so sort by (-was_here, -stab)
                return (-was_here, -stab)
            assigned_list.sort(key=keep_key, reverse=False)  # reverse False because we use negative in key
            # keep first cap, others to idle
            for comp in assigned_list[cap:]:
                desired[id(comp)] = 'idle'
                assigned_counts[group] -= 1
                assigned_counts['idle'] += 1

        # Now compute which drones would change group relative to current_group_for
        changes = []
        keeps = []
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            targ = desired.get(key, 'idle')
            # Validate targ exists in group_ids
            if targ not in group_ids:
                targ = 'idle'
                desired[key] = 'idle'
            if targ != curr:
                changes.append((comp, curr, targ))
            else:
                keeps.append((comp, curr, targ))

        # Enforce change_limit except allow all changes that are required to secure primary (we must fully protect primary).
        # Determine which changes are critical (those whose targ == primary_group)
        critical_changes = [ch for ch in changes if ch[2] == primary_group]
        non_critical_changes = [ch for ch in changes if ch[2] != primary_group]

        # We must ensure primary ends up with required_primary assigned. Count how many already kept or desired for primary
        already_for_primary = sum(1 for comp in drones if (desired.get(id(comp), current_group_for[comp]) == primary_group))
        # If already_for_primary < required_primary, we must allow enough critical changes
        required_primary_moves = max(0, required_primary - sum(1 for comp in drones if current_group_for[comp] == primary_group))
        # Build final_assignment, initially equal to current_group (keep)
        final_assignment: Dict[int, str] = {id(comp): current_group_for[comp] for comp in drones}

        # Determine how many change slots we can use
        allowed_changes = change_limit
        # But always allow critical changes sufficient to achieve primary protection
        # We'll enforce all critical_changes that contribute toward primary up to needed primary count;
        # If critical_changes are fewer than needed, other non-critical may need to move (shouldn't be typical)
        # First apply critical changes (all of them) to guarantee primary is filled (we need to ensure primary gets all desired).
        for comp, curr, targ in critical_changes:
            final_assignment[id(comp)] = targ

        # Count used change slots so far
        used_changes = len(critical_changes)
        # Allowed remaining
        remaining_slots = max(0, allowed_changes - used_changes)

        # Now we can select up to remaining_slots from non_critical_changes to apply
        # Prioritize non_critical_changes by willingness (low stability, idle current group preferred to change)
        def change_priority(ch):
            comp, curr, targ = ch
            key = id(comp)
            stab = self.stable_steps.get(key, 0)
            # we prefer to change low stability (smaller stab), and those currently idle or moving (not protecting)
            protecting_now = 1 if curr.startswith('protecting ') else 0
            # Also prefer those closer to their target (to reduce transit)
            # compute distance to target field if target is protecting
            dist_pen = 0.0
            if targ.startswith('protecting '):
                tid = targ.replace('protecting ', '')
                # find field object
                # note: we only stored field_by_group for threat_fields; it's fine
                field_obj = field_by_group.get(targ)
                if field_obj is not None:
                    dist_pen = self._dist_to_field(comp.location, field_obj)
            return (stab, protecting_now, dist_pen)
        non_critical_changes.sort(key=change_priority)

        for comp, curr, targ in non_critical_changes:
            if remaining_slots <= 0:
                break
            final_assignment[id(comp)] = targ
            remaining_slots -= 1

        # Any remaining non-selected changes will be kept at current assignment (final_assignment already has current)
        # Sanity check: ensure final counts do not overprotect and primary is fully protected
        # Fix if primary is still underprotected by forcing additional changes (override limit if necessary)
        final_counts = defaultdict(int)
        for comp in drones:
            grp = final_assignment.get(id(comp), current_group_for[comp])
            final_counts[grp] += 1
        if final_counts.get(primary_group, 0) < required_primary:
            # need extra drones for primary; find candidates currently not assigned to primary, sorted by low stability and distance
            candidates = [comp for comp in drones if final_assignment.get(id(comp), current_group_for[comp]) != primary_group]
            candidates.sort(key=lambda c: (self.stable_steps.get(id(c), 0), self._dist_to_field(c.location, primary_field)))
            need = required_primary - final_counts.get(primary_group, 0)
            for c in candidates[:need]:
                final_assignment[id(c)] = primary_group
                final_counts[primary_group] += 1

        # Apply final assignments via environment.assign_group and update prev/stability
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