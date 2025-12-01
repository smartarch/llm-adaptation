from typing import Dict, Any, List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map from component id -> last assigned group name
        self.prev_assignments: Dict[int, str] = {}
        # Map from component id -> consecutive steps it has been in the same group
        self.stable_steps: Dict[int, int] = {}
        # Keep the last step we processed (not strictly necessary but helpful)
        self.last_step = -1

    def _clamp_distance_to_field(self, loc, field) -> float:
        """Distance from loc to nearest point inside field rectangle."""
        # loc has x,y; field has left, right, top, bottom
        x = loc.x
        y = loc.y
        # clamp x,y to rectangle
        cx = min(max(x, field.left), field.right)
        cy = min(max(y, field.top), field.bottom)
        dx = x - cx
        dy = y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Setup basics
        drones = list(components)
        N = len(drones)
        half_min = (N + 1) // 2  # at least half (ceil)
        move_limit = N // 2      # allow changing at most floor(N/2) drones per step

        # Build valid protecting group names for current threatful fields
        threat_fields = [f for f in environment.fields if f.threat_level > 0]
        field_by_id = {f.id: f for f in environment.fields}
        protecting_groups = {f'protecting {f.id}': f for f in threat_fields}

        # Helper to get current group guess for a drone (based on previous assignment or its state)
        current_group_for = {}
        for comp in drones:
            key = id(comp)
            # If we have previous assignment from this controller and it's still valid, use it
            prev = self.prev_assignments.get(key)
            if prev in group_ids:
                current_group_for[comp] = prev
                continue
            # Else infer from component state / target_id
            if getattr(comp, 'target_id', None):
                name = f'protecting {comp.target_id}'
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
            # Note: do not update prev_assignments here; we'll update them after we finalize new assignments

        # If no threatful fields, assign all to idle
        if not threat_fields:
            for comp in drones:
                environment.assign_group(comp, 'idle')
                self.prev_assignments[id(comp)] = 'idle'
                # update stable steps if unchanged otherwise reset
                # if it was already 'idle' we incremented; else reset to 0 (already done above)
            self.last_step = step
            return

        # Pick primary (most threatened) field (highest threat_level, break ties by id)
        primary_field = max(threat_fields, key=lambda f: (f.threat_level, str(f.id)))
        primary_group = f'protecting {primary_field.id}'
        required_primary = max(0, int(primary_field.drones_for_full_protection))

        # Compute distances to primary
        distances = []
        for comp in drones:
            d = self._clamp_distance_to_field(comp.location, primary_field)
            distances.append((d, comp))
        distances.sort(key=lambda x: x[0])

        # Desired assignments mapping (initially None)
        desired: Dict[int, str] = {}

        # Choose closest drones for primary up to required_primary (but not exceeding N)
        num_primary_assigned = min(required_primary, N)
        primary_selected = [comp for (_, comp) in distances[:num_primary_assigned]]
        for comp in primary_selected:
            desired[id(comp)] = primary_group

        # Mark remaining drones pool
        remaining = [comp for comp in drones if id(comp) not in desired]

        # Attempt to fully protect secondary fields in descending threat order using remaining drones
        # For each field, we respect its required number, but don't overprotect.
        secondary_fields = sorted(
            [f for f in threat_fields if f.id != primary_field.id],
            key=lambda f: (f.threat_level, str(f.id)),
            reverse=True
        )
        # For fields, determine how many are already effectively assigned (from current_group_for)
        current_assignments_count = {}
        for f in threat_fields:
            name = f'protecting {f.id}'
            current_assignments_count[name] = 0
        for comp in drones:
            cg = current_group_for[comp]
            if cg in current_assignments_count:
                current_assignments_count[cg] += 1
        # Also account those we already selected for primary
        current_assignments_count[primary_group] = sum(1 for comp in primary_selected)

        # Try fully protect secondaries
        for field in secondary_fields:
            group_name = f'protecting {field.id}'
            required = int(field.drones_for_full_protection)
            already = current_assignments_count.get(group_name, 0)
            need = max(0, required - already)
            if need <= 0:
                # Already fully protected; attempt to keep those drones there by leaving them unchanged.
                continue
            # Pick the closest 'remaining' drones to this field
            if not remaining:
                break
            # compute distances to this field
            rem_dists = sorted([(self._clamp_distance_to_field(comp.location, field), comp) for comp in remaining], key=lambda x: x[0])
            to_assign = []
            for i in range(min(need, len(rem_dists))):
                to_assign.append(rem_dists[i][1])
            for comp in to_assign:
                desired[id(comp)] = group_name
            # update remaining
            remaining = [comp for comp in remaining if id(comp) not in desired]
            # update counts
            current_assignments_count[group_name] = current_assignments_count.get(group_name, 0) + len(to_assign)

        # After trying full protections, count how many will be protecting (desired or currently assigned and stable)
        protecting_count = 0
        # Desired protecting counts include desired selections and current ones that we haven't scheduled to change
        # For now count desired protecting
        for comp in drones:
            if desired.get(id(comp)) and desired[id(comp)].startswith('protecting '):
                protecting_count += 1
            else:
                # If no desired assignment yet but current_group_for is protecting and in group_ids, count it for now
                cg = current_group_for[comp]
                if cg.startswith('protecting ') and cg in group_ids:
                    protecting_count += 1

        # If protecting_count < half_min, use remaining drones (closest to highest threat fields) to reach half_min.
        if protecting_count < half_min:
            need_more = half_min - protecting_count
            if remaining:
                # Rank remaining drones by proximity to highest-threat fields (primary first)
                # We'll create a priority (min distance to any threat field, weighted by field threat)
                field_list_sorted = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
                rem_priority = []
                for comp in remaining:
                    # compute minimal weighted distance (distance / threat_level) to prefer closeness to high threat fields
                    best_score = float('inf')
                    best_field = None
                    for f in field_list_sorted:
                        d = self._clamp_distance_to_field(comp.location, f)
                        # smaller threat => worse score; we divide by threat_level (add small epsilon)
                        tq = max(0.001, f.threat_level)
                        score = d / tq
                        if score < best_score:
                            best_score = score
                            best_field = f
                    rem_priority.append((best_score, comp, best_field))
                rem_priority.sort(key=lambda x: x[0])
                assigned_more = 0
                for _, comp, best_field in rem_priority:
                    if assigned_more >= need_more:
                        break
                    if best_field is None:
                        continue
                    desired[id(comp)] = f'protecting {best_field.id}'
                    assigned_more += 1
                remaining = [comp for comp in remaining if id(comp) not in desired]

        # Any drone not in desired yet will be idle (we prefer not to partially protect many fields)
        for comp in remaining:
            desired[id(comp)] = 'idle'

        # Now enforce the movement/stability constraint: do not change more than move_limit drones.
        # Compute which drones would change group relative to current_group_for
        would_change = []
        would_keep = []
        for comp in drones:
            key = id(comp)
            curr = current_group_for[comp]
            targ = desired.get(key, 'idle')
            # If target group doesn't exist in group_ids (e.g., protecting a field that lost threat), fallback to idle
            if targ not in group_ids:
                targ = 'idle'
                desired[key] = 'idle'
            if targ != curr:
                would_change.append((comp, curr, targ))
            else:
                would_keep.append((comp, curr, targ))

        # If too many moves, select a subset to actually change, prioritizing changes for drones with low stability and those not currently protecting.
        final_assignment: Dict[int, str] = {}
        if len(would_change) <= move_limit:
            # Accept all changes
            for comp, _, targ in would_change:
                final_assignment[id(comp)] = targ
            for comp, curr, _ in would_keep:
                final_assignment[id(comp)] = curr
        else:
            # Sort change candidates by desirability to change:
            # Candidates with smaller stable_steps and those not currently protecting are more desirable to change.
            def change_priority(item):
                comp, curr, targ = item
                key = id(comp)
                stable = self.stable_steps.get(key, 0)
                currently_protecting = 1 if curr.startswith('protecting ') else 0
                # Lower stable -> higher priority to change (so sort ascending)
                # not currently_protecting (i.e., idle) are more desirable to change, so invert currently_protecting
                return (stable, currently_protecting)

            sorted_changes = sorted(would_change, key=change_priority)
            # pick first move_limit to change
            to_change_set = set()
            for i in range(move_limit):
                comp, curr, targ = sorted_changes[i]
                to_change_set.add(id(comp))
            # For those selected to change, apply desired target; for others, keep current
            for comp, curr, targ in would_change:
                key = id(comp)
                if key in to_change_set:
                    final_assignment[key] = targ
                else:
                    # Keep current group
                    # But ensure current group is valid; if not, fallback to 'idle'
                    if curr in group_ids:
                        final_assignment[key] = curr
                    else:
                        final_assignment[key] = 'idle'
            for comp, curr, targ in would_keep:
                final_assignment[id(comp)] = curr

        # Final sanity: ensure all components have an assignment, and group exists in group_ids
        for comp in drones:
            key = id(comp)
            group = final_assignment.get(key)
            if group not in group_ids:
                # fallback: if the group's field no longer threatened, assign idle
                group = 'idle'
            final_assignment[key] = group

        # Apply assignments via environment.assign_group and update prev_assignments & stable_steps
        for comp in drones:
            key = id(comp)
            group = final_assignment[key]
            environment.assign_group(comp, group)
            prev = self.prev_assignments.get(key)
            # Update stable_steps based on whether this assignment equals previous
            if prev == group:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0
            self.prev_assignments[key] = group

        self.last_step = step