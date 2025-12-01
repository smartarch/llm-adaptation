Reasoning and adaptation strategy

Goal summary
- Always fully protect the single most threatened field using the closest drones.
- Avoid overprotection: do not assign more drones to a field than field.drones_for_full_protection.
- Prefer fully protecting a few fields rather than partially protecting many.
- Keep churn low: prefer to keep drones that are already protecting a field assigned to that same field.
- Make sure at least half of the drones are used for protection most of the time; if after protecting the top field (and optionally more fields) fewer than half the drones are protecting, assign additional drones (preferably without breaking existing protectors) to the highest-threat remaining fields to reach half.
- When selecting drones for a field, use an ordered priority that keeps current protectors and movers-to-that-field first, then idle drones, then other drones sorted by closeness. This gives the "closest drones" requirement while respecting stickiness.

How the algorithm works (step-by-step)
1. Collect fields with threat_level > 0 and sort them by descending threat_level.
2. Compute the "sticky" groups:
   - protectors_by_field: drones currently in state "protecting" for each field
   - movers_by_field: drones currently "moving_to_field" targeting a field
   - idle drones list
   - other drones (protecting other fields or moving elsewhere)
3. First preserve any fields that are already fully protected (i.e., they already have at least drones_for_full_protection protectors). Keep exactly drones_for_full_protection there (prefer the ones already protecting) and mark them assigned.
4. Ensure the most threatened field is fully protected:
   - If it already is, keep its drones (no churn).
   - Otherwise, select drones up to drones_for_full_protection for that field by the following priority order: already protecting → moving-to-that-field → idle → other drones (sorted by Euclidean distance to the field center). This ensures closest drones end up protecting the most threatened field.
5. For subsequent fields (by threat rank), attempt to fully protect them provided enough unassigned drones exist and without breaking sticky protectors of other fields if possible. Follow the same selection priority for each.
6. Make sure at least half of drones are assigned to some protecting group. If not reached after previous steps, assign more drones to the remaining highest-threat fields (filling them up if possible, otherwise partially) until the “at least half” requirement is satisfied. When forced to partially protect, prefer using idle or movers-to-that-field before taking protectors of other fields.
7. Any remaining unassigned drones become idle.
8. Explicitly assign every drone to a group using environment.assign_group(component, group_id). (Even when a drone remains doing the same action, it must be explicitly re-assigned to the same group.)

This approach respects:
- Always fully protecting the most threatened field with the closest (and sticky) drones.
- No overprotection.
- Preference for fewer fully protected fields over many partial protections.
- Low churn by preferring to keep current protectors in place.
- Ensuring at least half of drones are generally used for protection.

Implementation
Below is the Python implementation as a SmartFarmAdaptation class deriving from FarmAdaptation.

```py
from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance_to_field(self, comp, field):
        cx, cy = self._field_center(field)
        return hypot(comp.location.x - cx, comp.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to get group name for a field
        def protecting_group(field_id):
            return f"protecting {field_id}"

        total_drones = len(components)
        if total_drones == 0:
            return

        min_protectors = ceil(total_drones / 2)  # at least half should be protecting

        # Fields with nonzero threat, sorted by descending threat_level then id
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Quick mapping from field id to field object
        field_by_id = {f.id: f for f in fields}

        # Group drones by current observable state/target
        protectors_by_field = defaultdict(list)
        movers_by_field = defaultdict(list)
        idle_drones = []
        other_drones = []  # drones protecting/moving to other fields or unknown

        for comp in components:
            if comp.state == "protecting" and comp.target_id is not None:
                protectors_by_field[comp.target_id].append(comp)
            elif comp.state == "moving_to_field" and comp.target_id is not None:
                movers_by_field[comp.target_id].append(comp)
            elif comp.state == "idle":
                idle_drones.append(comp)
            else:
                other_drones.append(comp)

        # Prepare assignment tracking
        assigned = {}  # comp -> group_name

        # Utility to mark a component assigned
        def mark_assigned(comp, group_name):
            assigned[comp] = group_name

        # First, preserve any field that is already fully protected (keep exactly required number)
        for f in fields:
            required = int(f.drones_for_full_protection)
            cur_protectors = protectors_by_field.get(f.id, [])
            if len(cur_protectors) >= required and protecting_group(f.id) in group_ids:
                # Keep the first `required` protectors (they are already protecting)
                kept = cur_protectors[:required]
                for c in kept:
                    mark_assigned(c, protecting_group(f.id))

        # Helper to gather candidates for a field in priority order:
        # 1) already protecting that field (but not yet assigned)
        # 2) moving-to-that-field (but not yet assigned)
        # 3) idle drones (not yet assigned)
        # 4) other drones (not yet assigned), sorted by distance
        def gather_candidates(field):
            fid = field.id
            candidates = []
            # protectors for that field
            for c in protectors_by_field.get(fid, []):
                if c not in assigned:
                    candidates.append((0, c))
            # movers for that field
            for c in movers_by_field.get(fid, []):
                if c not in assigned:
                    candidates.append((1, c))
            # idle drones
            for c in idle_drones:
                if c not in assigned:
                    candidates.append((2, c))
            # other drones sorted by distance
            others = []
            for c in components:
                if c in assigned:
                    continue
                # skip those already included above
                if c in protectors_by_field.get(fid, []) or c in movers_by_field.get(fid, []) or c in idle_drones:
                    continue
                # c is some other drone (protecting/moving elsewhere)
                d = self._distance_to_field(c, field)
                others.append((d, c))
            # sort other drones by distance
            others.sort(key=lambda x: x[0])
            # map others to a lower priority number (3) but preserve closeness ordering
            for d, c in others:
                candidates.append((3, c))
            # Now sort candidates by their priority tag then (for same tag) by distance to field
            def cand_key(item):
                tag, comp = item
                return (tag, self._distance_to_field(comp, field))
            candidates.sort(key=cand_key)
            # Return ordered list of components
            return [comp for tag, comp in candidates]

        # Force-protect the most threatened field first (always)
        if fields:
            top = fields[0]
            top_group = protecting_group(top.id)
            if top_group in group_ids:
                required = int(top.drones_for_full_protection)
                # Count already-assigned protectors for top
                already = [c for c, g in assigned.items() if g == top_group]
                needed = max(0, required - len(already))
                if needed > 0:
                    candidates = gather_candidates(top)
                    for c in candidates:
                        if needed <= 0:
                            break
                        if c in assigned:
                            continue
                        mark_assigned(c, top_group)
                        needed -= 1
                # If there were more already assigned than required (due to earlier preserved full fields), trim extras:
                assigned_to_top = [c for c, g in assigned.items() if g == top_group]
                if len(assigned_to_top) > required:
                    # Prefer to keep those that were originally protecting first
                    orig_protectors = [c for c in protectors_by_field.get(top.id, []) if c in assigned_to_top]
                    keep = set(orig_protectors[:required])
                    # fill up keep with closest among assigned_to_top if not enough original protectors
                    if len(keep) < required:
                        others = [c for c in assigned_to_top if c not in keep]
                        others.sort(key=lambda comp: self._distance_to_field(comp, top))
                        for c in others:
                            if len(keep) >= required:
                                break
                            keep.add(c)
                    # unassign extras
                    for c in assigned_to_top:
                        if c not in keep:
                            del assigned[c]

        # After ensuring top field, try to fully protect other fields (in threat order)
        # but be conservative: do not break existing preserved protectors if avoidable.
        for f in fields[1:]:
            group_name = protecting_group(f.id)
            if group_name not in group_ids:
                continue
            required = int(f.drones_for_full_protection)
            # How many already assigned to this field?
            already_assigned = [c for c, g in assigned.items() if g == group_name]
            needed = max(0, required - len(already_assigned))
            if needed <= 0:
                continue  # already fully protected
            # Determine how many unassigned drones are available
            unassigned_drones = [c for c in components if c not in assigned]
            if len(unassigned_drones) < needed:
                # Not enough free drones to fully protect this field; skip for now (we prefer fully protecting fewer fields)
                continue
            # Gather candidates and pick needed drones
            candidates = gather_candidates(f)
            picked = 0
            for c in candidates:
                if picked >= needed:
                    break
                if c in assigned:
                    continue
                mark_assigned(c, group_name)
                picked += 1

        # Count protectors so far
        current_protectors_count = sum(1 for g in assigned.values() if g != "idle")

        # Ensure at least half of drones are used for protection
        if current_protectors_count < min_protectors:
            needed_more = min_protectors - current_protectors_count
            # Try to fill remaining needs by assigning to highest-threat fields (in order),
            # filling up to their required (without overprotection).
            for f in fields:
                if needed_more <= 0:
                    break
                group_name = protecting_group(f.id)
                if group_name not in group_ids:
                    continue
                required = int(f.drones_for_full_protection)
                already_assigned = [c for c, g in assigned.items() if g == group_name]
                free_slots = max(0, required - len(already_assigned))
                if free_slots <= 0:
                    continue
                # Number to assign here is min(free_slots, needed_more)
                to_assign = min(free_slots, needed_more)
                candidates = gather_candidates(f)
                picked = 0
                for c in candidates:
                    if picked >= to_assign:
                        break
                    if c in assigned:
                        continue
                    mark_assigned(c, group_name)
                    picked += 1
                    needed_more -= 1
                # continue to next field if still need more
            # If still not satisfied (rare, e.g., insufficient fields to protect), assign remaining needed_more to the top field's group
            # without exceeding its capacity (shouldn't happen because we respected capacities), otherwise assign to idle? We'll assign to any field with capacity.
            if needed_more > 0:
                for f in fields:
                    if needed_more <= 0:
                        break
                    group_name = protecting_group(f.id)
                    required = int(f.drones_for_full_protection)
                    already_assigned = [c for c, g in assigned.items() if g == group_name]
                    free_slots = max(0, required - len(already_assigned))
                    if free_slots <= 0:
                        continue
                    candidates = gather_candidates(f)
                    picked = 0
                    for c in candidates:
                        if picked >= free_slots or needed_more <= 0:
                            break
                        if c in assigned:
                            continue
                        mark_assigned(c, group_name)
                        picked += 1
                        needed_more -= 1

        # Finally assign all remaining unassigned drones to idle
        for c in components:
            if c not in assigned:
                assigned[c] = "idle"

        # Perform actual environment assignments (explicitly assign every drone)
        for comp, group in assigned.items():
            # safety: group should be valid; fall back to idle if not
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)
```