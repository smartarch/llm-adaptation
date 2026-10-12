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