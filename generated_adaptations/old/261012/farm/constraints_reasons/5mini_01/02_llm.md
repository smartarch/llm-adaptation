Reasoning and adaptation strategy

Goal summary
- Always fully protect the single most threatened field using the closest drones (use exactly field.drones_for_full_protection drones).
- Avoid overprotection: never assign more drones than required for full protection to any field.
- Favor stability: keep drones that are already protecting a field on that field when possible (minimize reassignments).
- Favor proximity: when selecting additional drones, prefer drones that are already moving toward that field and then the closest idle/other drones.
- Prefer fully protecting fewer fields rather than partially protecting many. After ensuring the most threatened field is fully protected, try to fully protect other fields (next highest threat) only if we have enough drones to meet their full requirement.
- Keep at least half of the fleet assigned to protection if possible. If after fully protecting as many fields as we can the number of protecting drones is still below half, we assign remaining drones to the next-highest-threat field(s) partially (closest first) until roughly half of the drones are protecting. This meets the functional requirement to have not too many idle drones, while still preferring full protections when possible.
- Maintain stability across steps by prioritizing drones that are already protecting or moving toward the field when selecting assignments. This ensures at least a portion of drones remain on the same assignment over time.

Detailed assignment algorithm
1. If there are no fields with threat_level > 0, assign every drone to "idle".
2. Choose the most threatened field (highest threat_level). Ties broken deterministically by field id ordering.
3. For that main field:
   - Keep drones that are already protecting it (state == "protecting" and target_id == field.id).
   - Count moving_to_field drones (state == "moving_to_field" and target_id == field.id) as favorable because they are already en-route.
   - If still short of the required number (drones_for_full_protection), select additional drones from the remaining fleet ordered by a preference score (idle preferred over switching from protecting another field) and by distance to the field center.
   - If more drones are currently protecting the main field than needed, pick the closest required number to continue protecting and free the rest for other assignments (to avoid overprotection).
4. For other fields in descending threat order:
   - Attempt to fully protect each in turn using the remaining free drones, using the same preference/stability ordering (already protecting that field, moving to it, then idle, then protecting others).
   - Do not overprotect any field.
5. After attempting full protection for as many fields as possible, ensure at least half of drones are protecting. If not, allocate remaining drones (closest-first) to the next best fields partially (still avoiding overprotection) until at least half are protecting or until there are no more fields or drones.
6. Any drones left unassigned after these steps are set to "idle".
7. For every component, call environment.assign_group(component, group_id) exactly once.

This balances the requirements: main field is fully protected with the closest drones, we avoid overprotection, maximize number of drones used for protection (at least half when possible), and prioritize stability by keeping existing protectors and en-route drones on their field.

Code (implementation)

```py
from typing import List, Dict, Tuple
from math import hypot

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist(self, loc, cx, cy):
        try:
            return hypot(loc.x - cx, loc.y - cy)
        except Exception:
            return float("inf")

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: build map of fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not components:
            return  # nothing to assign

        # If no threatened fields, assign all to idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat desc, tie-breaker by id for determinism
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Precompute centers
        field_centers = {f.id: self._field_center(f) for f in threatened_fields}

        # Utility: group name for a field id
        def group_name_for(fid):
            return f"protecting {fid}"

        total_drones = len(components)

        # Track assignments we plan: field_id -> list of drones
        planned: Dict[str, List] = {f.id: [] for f in threatened_fields}
        idle_list: List = []

        # Build convenience lists of current states to encourage stability
        currently_protecting: Dict[str, List] = {f.id: [] for f in threatened_fields}
        currently_moving_to: Dict[str, List] = {f.id: [] for f in threatened_fields}
        others: List = []

        # Map component id (object) to avoid duplicates
        remaining = set(components)

        for c in components:
            # Identify which threatened field (if any) the drone is protecting/moving_to
            target = getattr(c, "target_id", None)
            state = getattr(c, "state", None)
            if target in currently_protecting and state == "protecting":
                currently_protecting[target].append(c)
            elif target in currently_moving_to and state == "moving_to_field":
                currently_moving_to[target].append(c)
            else:
                others.append(c)

        # Select main field (highest threat)
        main_field = threatened_fields[0]
        main_id = main_field.id
        main_required = max(0, int(getattr(main_field, "drones_for_full_protection", 0)))

        # Helper to sort candidates by preference and distance for a specific field
        def candidate_sort_key_for_field(c, fid):
            cx, cy = field_centers[fid]
            dist = self._dist(c.location, cx, cy)
            # Preference order (lower is better)
            # already protecting that field -> 0
            # moving to that field -> 1
            # idle -> 2
            # protecting other field -> 3
            # moving to other field -> 4
            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)
            if state == "protecting" and target == fid:
                pref = 0
            elif state == "moving_to_field" and target == fid:
                pref = 1
            elif state == "idle" or target is None:
                pref = 2
            elif state == "protecting":
                pref = 3
            else:
                pref = 4
            return (pref, dist)

        # Allocate for main field
        # Start with current protectors (avoid moving them unless surplus)
        main_cur = list(currently_protecting.get(main_id, []))
        main_moving = list(currently_moving_to.get(main_id, []))

        # If more currently protecting than required, keep the closest 'required' of them
        if len(main_cur) >= main_required:
            # sort by distance and choose required ones
            cx, cy = field_centers[main_id]
            main_cur.sort(key=lambda c: self._dist(c.location, cx, cy))
            chosen = main_cur[:main_required]
            planned[main_id].extend(chosen)
            for c in chosen:
                if c in remaining:
                    remaining.remove(c)
            # Those extra currently protecting beyond required become available
            extras = main_cur[main_required:]
            for c in extras:
                if c not in remaining:
                    remaining.add(c)
        else:
            # Keep all current protectors
            planned[main_id].extend(main_cur)
            for c in main_cur:
                if c in remaining:
                    remaining.remove(c)
            # Count how many more needed
            needed = main_required - len(planned[main_id])
            # Include moving-to-main drones next
            # keep moving_to that field
            cx, cy = field_centers[main_id]
            main_moving.sort(key=lambda c: self._dist(c.location, cx, cy))
            take = main_moving[:needed]
            planned[main_id].extend(take)
            for c in take:
                if c in remaining:
                    remaining.remove(c)
            needed = main_required - len(planned[main_id])
            if needed > 0:
                # Choose from remaining drones sorted by candidate preference and distance
                remaining_list = list(remaining)
                remaining_list.sort(key=lambda c: candidate_sort_key_for_field(c, main_id))
                take2 = remaining_list[:needed]
                planned[main_id].extend(take2)
                for c in take2:
                    if c in remaining:
                        remaining.remove(c)

        # Ensure we never exceed required
        if len(planned[main_id]) > main_required:
            planned[main_id] = planned[main_id][:main_required]

        # Now try to fully protect other fields in order of descending threat
        for f in threatened_fields[1:]:
            fid = f.id
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if req == 0:
                continue
            # Prefer currently protecting this field
            cur = list(currently_protecting.get(fid, []))
            moving = list(currently_moving_to.get(fid, []))
            chosen_for_field: List = []

            # Keep current protectors (but not more than req)
            if cur:
                cx, cy = field_centers[fid]
                cur.sort(key=lambda c: self._dist(c.location, cx, cy))
                selected = cur[:req]
                chosen_for_field.extend(selected)
                for c in selected:
                    if c in remaining:
                        remaining.remove(c)

            # If still need more, take moving
            if len(chosen_for_field) < req and moving:
                cx, cy = field_centers[fid]
                moving.sort(key=lambda c: self._dist(c.location, cx, cy))
                need = req - len(chosen_for_field)
                mv_take = [c for c in moving if c in remaining][:need]
                chosen_for_field.extend(mv_take)
                for c in mv_take:
                    if c in remaining:
                        remaining.remove(c)

            # If still need more, take closest remaining (favor idles)
            if len(chosen_for_field) < req and remaining:
                rem_list = list(remaining)
                rem_list.sort(key=lambda c: candidate_sort_key_for_field(c, fid))
                need = req - len(chosen_for_field)
                take = rem_list[:need]
                chosen_for_field.extend(take)
                for c in take:
                    if c in remaining:
                        remaining.remove(c)

            # Assign chosen to this field (may be fewer than req if not enough drones)
            planned[fid].extend(chosen_for_field)

        # Count how many are assigned to protection
        assigned_protection_count = sum(len(v) for v in planned.values())

        # Ensure at least half of drones are protecting if possible
        min_protect = (total_drones + 1) // 2  # ceil half
        if assigned_protection_count < min_protect and threatened_fields:
            # We will try to assign remaining drones (closest-first) to next best fields,
            # allowing partial protection but still never exceeding any field's required capacity.
            # Build list of fields ordered by threat (already in that order), and for each find remaining capacity
            for f in threatened_fields:
                if assigned_protection_count >= min_protect:
                    break
                fid = f.id
                capacity = max(0, int(getattr(f, "drones_for_full_protection", 0))) - len(planned[fid])
                # If no capacity but we still want to partially add (i.e., req could be 0),
                # we allow adding up to req; but we don't overprotect.
                if capacity <= 0:
                    continue
                # Fill capacity with closest remaining drones
                if not remaining:
                    break
                rem_list = list(remaining)
                rem_list.sort(key=lambda c: candidate_sort_key_for_field(c, fid))
                need = min(capacity, min_protect - assigned_protection_count)
                take = rem_list[:need]
                planned[fid].extend(take)
                for c in take:
                    if c in remaining:
                        remaining.remove(c)
                assigned_protection_count = sum(len(v) for v in planned.values())

        # Any drones still remaining -> idle
        idle_list = list(remaining)

        # Now call environment.assign_group for every component exactly once:
        # For drones assigned to fields, use "protecting {field.id}", others to "idle".
        # To ensure deterministic behavior, build an assignment map from component -> group
        assignment_map = {}

        for fid, lst in planned.items():
            grp = group_name_for(fid)
            # Only assign to valid group ids; if group id missing (should not happen), fallback to idle
            if grp not in group_ids:
                grp = "idle"
            for c in lst:
                assignment_map[c] = grp

        for c in idle_list:
            assignment_map[c] = "idle"

        # As fallback for any components not in assignment_map (shouldn't happen), set to idle
        for c in components:
            if c not in assignment_map:
                assignment_map[c] = "idle"

        # Finally apply assignments
        for c, g in assignment_map.items():
            environment.assign_group(c, g)
```