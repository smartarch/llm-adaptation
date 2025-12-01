from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track last group we commanded for each drone (keyed by id(component))
        self.prev_assigned = {}
        # consecutive steps the drone has been assigned the same group
        self.streak = {}

    def _dist2(self, loc, point):
        dx = (loc.x if hasattr(loc, 'x') else loc[0]) - point[0]
        dy = (loc.y if hasattr(loc, 'y') else loc[1]) - point[1]
        return dx * dx + dy * dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to form group name for a field
        def protect_group(field_id):
            return f"protecting {field_id}"

        # Map component id to component for quick lookup
        comp_by_id = {id(c): c for c in components}
        total_drones = len(components)

        # Current observed behavior-based groups for each component (based on state and target)
        observed_group = {}
        for c in components:
            if c.state in ("protecting", "moving_to_field") and c.target_id:
                observed_group[id(c)] = protect_group(c.target_id)
            else:
                observed_group[id(c)] = "idle"

        # Update streak counters based on what we commanded previously (persistence info)
        # Note: prev_assigned holds last commanded group (or None)
        for c in components:
            cid = id(c)
            last = self.prev_assigned.get(cid)
            # If we commanded the same group last step and observed it still same, increment streak
            if last is not None and last == observed_group.get(cid):
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                # reset streak if changed
                self.streak[cid] = 0

        # Prepare fields of interest (threat > 0), sorted by descending threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        field_centers = {}
        for f in fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Count currently protecting drones per field (observed state)
        current_protecting = {}
        protecting_drones_list = []  # list of component ids currently protecting any field
        for f in fields:
            current_protecting[f.id] = []

        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id:
                tid = c.target_id
                if tid in current_protecting:
                    current_protecting[tid].append(cid)
                protecting_drones_list.append(cid)

        num_currently_protecting = len(protecting_drones_list)

        # Move limit: how many protecting drones we allow to reassign in this step (at most half)
        max_reassign_from_protecting = num_currently_protecting // 2

        # We will plan assignments per component id -> group string
        planned = {}

        # Start by reserving already-protecting drones for their fields (we may keep them)
        # We also mark them as initially assigned to their observed protecting group (so they are counted)
        for cid in protecting_drones_list:
            planned[cid] = observed_group[cid]  # typically "protecting {field_id}"

        # Bookkeeping: which components are still free to assign (not yet used to reach requirements)
        free_components = set(id(c) for c in components) - set(planned.keys())

        # For assignment purposes, also consider protecting drones we may reassign (but they are not in free_components)
        # We maintain movable_protecting set = protecting drones assigned to other fields we can consider moving if needed.
        # We'll determine which protecting drones are 'locked' (not allowed to move) based on streak and previous assignment:
        # Lock drones that: are protecting and we commanded them previously to be protecting this same field (persistence).
        locked_protecting = set()
        movable_protecting = set()
        for cid in protecting_drones_list:
            last_cmd = self.prev_assigned.get(cid)
            obs_group = observed_group.get(cid)
            # If we commanded them previously to the same observed protecting group, treat as locked (prefer not to move)
            if last_cmd is not None and last_cmd == obs_group and self.streak.get(cid, 0) >= 0:
                locked_protecting.add(cid)
            else:
                movable_protecting.add(cid)
        # We should never move locked_protecting drones.

        # Function to pick nearest free/movable drones to a field center.
        def pick_closest_for_field(field_id, needed, allowed_move_from_protecting):
            picked = []
            if needed <= 0:
                return picked

            center = field_centers[field_id]

            # Candidate lists: idle/moving (free_components) first; then movable_protecting (if allowed)
            candidates = []
            for cid in list(free_components):
                comp = comp_by_id[cid]
                # compute distance
                d2 = self._dist2(comp.location, center)
                candidates.append((d2, cid, False))  # False meaning not currently protecting someone

            # If we still need after idle/moving, include movable protecting drones but only up to allowed limit
            movable_list = []
            for cid in movable_protecting:
                # skip if already planned to protect this same field (shouldn't be here)
                if planned.get(cid) == protect_group(field_id):
                    continue
                comp = comp_by_id[cid]
                d2 = self._dist2(comp.location, center)
                movable_list.append((d2, cid, True))  # True = currently protecting others

            # sort both lists
            candidates.sort(key=lambda x: x[0])
            movable_list.sort(key=lambda x: x[0])

            # choose from candidates first
            for entry in candidates:
                if needed <= 0:
                    break
                _, cid, _ = entry
                picked.append(cid)
                free_components.discard(cid)
                needed -= 1

            # choose from movable protecting but respect allowed_move_from_protecting cap
            moves_allowed = allowed_move_from_protecting
            for entry in movable_list:
                if needed <= 0 or moves_allowed <= 0:
                    break
                _, cid, _ = entry
                picked.append(cid)
                # mark this protecting drone as moved (remove from movable_protecting so it's not used twice)
                movable_protecting.discard(cid)
                # Also remove from planned (it was originally planned to continue protecting its previous field)
                if cid in planned:
                    del planned[cid]
                moves_allowed -= 1
                needed -= 1

            return picked

        # Allocation plan step 1: ensure the top-threat field is fully protected
        assigned_protection_count = 0
        assigned_to_field = {}  # field_id -> list of cids assigned by plan

        if fields:
            top = fields[0]
            top_id = top.id
            required = getattr(top, "drones_for_full_protection", 0)
            # count how many currently protecting that top field (already planned to stay)
            currently = current_protecting.get(top_id, [])
            currently_count = len(currently)
            # If there are more than required currently, keep exactly required and free the extra protecting drones (they observed protecting but field requires fewer)
            # However instruction: "If the field is already fully protected, keep the drones there to continue protection." If currently > required, treat only required as kept and free extras.
            # We'll keep the closest 'required' ones among the currently protecting (to match "closest drones" requirement as well).
            if currently_count > 0:
                # sort current protecting by distance to center and keep closest 'required' (others become movable_protecting)
                center = field_centers[top_id]
                cur_list = []
                for cid in currently:
                    comp = comp_by_id[cid]
                    d2 = self._dist2(comp.location, center)
                    cur_list.append((d2, cid))
                cur_list.sort(key=lambda x: x[0])
                keep_list = [cid for (_, cid) in cur_list[:required]]
                extra = [cid for (_, cid) in cur_list[required:]]
                # lock / keep the keep_list in planned, release extras for possible reassignment
                assigned_to_field[top_id] = list(keep_list)
                for cid in keep_list:
                    planned[cid] = protect_group(top_id)
                # extras: remove from planned and add to movable_protecting if appropriate
                for cid in extra:
                    if cid in planned:
                        del planned[cid]
                    # these extra protecting drones can be considered movable now (they are currently protecting another field)
                    movable_protecting.add(cid)
                    if cid in protecting_drones_list:
                        # they remain part of protecting_drones_list but are movable
                        pass
                currently_count = len(keep_list)
            else:
                assigned_to_field[top_id] = []

            # need more to reach required
            need_more = max(0, required - currently_count)
            # allowable moves from protecting drones (we already have movable_protecting set)
            # but ensure we don't move locked_protecting drones
            # allowed_move_from_protecting is at most max_reassign_from_protecting
            allowed_move = max_reassign_from_protecting
            # exclude any of the movable_protecting that are currently in top field (they shouldn't be)
            allowed_move_candidates = movable_protecting.copy()

            picked = pick_closest_for_field(top_id, need_more, allowed_move)
            for cid in picked:
                planned[cid] = protect_group(top_id)
                assigned_to_field[top_id].append(cid)

            # finalize assigned protection count
            assigned_protection_count = sum(len(v) for v in assigned_to_field.values())

        # Allocation step 2: try to fully protect additional fields greedily until we either run out of drones
        # or reach at least half the drones assigned to protection
        half_needed = (total_drones + 1) // 2  # ceil of half
        # Note: assigned_protection_count currently includes only top field assignment; we may include existing planned protecting in other fields as well
        # Initialize assigned_to_field entries for other fields with any currently protecting we decided to keep above (planned may contain some)
        for f in fields:
            if f.id not in assigned_to_field:
                assigned_to_field[f.id] = []
                # if any currently protecting drones for this field and we haven't removed them, include them
                for cid in current_protecting.get(f.id, []):
                    # if we already removed (e.g., extras moved), skip
                    if cid in planned and planned[cid] == protect_group(f.id):
                        assigned_to_field[f.id].append(cid)

        assigned_protection_count = sum(len(v) for v in assigned_to_field.values())

        # Attempt to fully protect next fields in order
        for f in fields[1:]:  # skip top (already handled)
            if assigned_protection_count >= total_drones:
                break
            field_id = f.id
            required = getattr(f, "drones_for_full_protection", 0)
            # count how many we currently have planned for this field
            currently_planned = len(assigned_to_field.get(field_id, []))
            need = max(0, required - currently_planned)
            if need == 0:
                continue  # already fully protected (or no drones needed)
            # See if we have enough free components + allowed movable protecting to cover need
            # allowed moves from protecting for this field should respect max_reassign_from_protecting remaining
            # Recalculate remaining allowed_move_from_protecting based on how many protecting we already decided to reassign
            # Estimate how many protecting we've planned to move away: count of planned earlier that were from movable_protecting removal
            # For simplicity, compute how many protecting drones are currently still planned (i.e., planned entries that were protecting)
            still_protecting_planned = [cid for cid, grp in planned.items() if grp != "idle" and grp.startswith("protecting")]
            num_protecting_planned = len(still_protecting_planned)
            # remaining allowed to reassign = floor(total_currently_protecting/2) - number_already_reassigned (approx)
            # number already reassigned equals original protecting count - number still protecting planned
            already_reassigned = num_currently_protecting - num_protecting_planned
            remaining_move_allowed = max(0, max_reassign_from_protecting - already_reassigned)

            picked = pick_closest_for_field(field_id, need, remaining_move_allowed)
            for cid in picked:
                planned[cid] = protect_group(field_id)
                assigned_to_field[field_id].append(cid)
                assigned_protection_count += 1

            # If we have now fully protected this field, assigned_protection_count updated via assigned_to_field lengths

            # If we've reached at least half of drones assigned to protection, stop attempting to fully protect more fields
            total_assigned_protection = sum(len(v) for v in assigned_to_field.values())
            if total_assigned_protection >= half_needed:
                assigned_protection_count = total_assigned_protection
                break

        # Allocation step 3: If after full allocations we still have fewer than half drones protecting, do a partial assignment to next-best field
        total_assigned_protection = sum(len(v) for v in assigned_to_field.values())
        if total_assigned_protection < half_needed:
            # find next best field that we haven't assigned to (or assigned partially)
            for f in fields:
                field_id = f.id
                # skip if this field already has some assigned and we prefer not to add partial if it's already been considered fully
                required = getattr(f, "drones_for_full_protection", 0)
                currently_planned = len(assigned_to_field.get(field_id, []))
                # available to add = needed to reach half_needed
                need = half_needed - total_assigned_protection
                if need <= 0:
                    break
                # We will pick closest free/movable drones for this field, but limit moving protecting drones as before
                # recompute remaining allowed reassign from protecting
                still_protecting_planned = [cid for cid, grp in planned.items() if grp != "idle" and grp.startswith("protecting")]
                num_protecting_planned = len(still_protecting_planned)
                already_reassigned = num_currently_protecting - num_protecting_planned
                remaining_move_allowed = max(0, max_reassign_from_protecting - already_reassigned)
                picked = pick_closest_for_field(field_id, need, remaining_move_allowed)
                for cid in picked:
                    planned[cid] = protect_group(field_id)
                    assigned_to_field.setdefault(field_id, []).append(cid)
                    total_assigned_protection += 1
                if total_assigned_protection >= half_needed:
                    break

        # At this point planned contains assigned protecting drones and some drones remain unplanned -> assign them to idle
        for c in components:
            cid = id(c)
            if cid not in planned:
                planned[cid] = "idle"

        # Final pass: ensure no field is overprotected (trim to drones_for_full_protection)
        # For each field, if planned count > drones_for_full_protection, release the farthest ones back to idle
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            p_list = [cid for cid, grp in planned.items() if grp == protect_group(fid)]
            if len(p_list) > req:
                # sort p_list by distance to field center, keep closest req, others -> idle
                center = field_centers[fid]
                arr = []
                for cid in p_list:
                    comp = comp_by_id[cid]
                    d2 = self._dist2(comp.location, center)
                    arr.append((d2, cid))
                arr.sort(key=lambda x: x[0])
                keep = set(cid for (_, cid) in arr[:req])
                for (_, cid) in arr[req:]:
                    planned[cid] = "idle"

        # Finally, apply the assignments via environment.assign_group for each component
        for c in components:
            cid = id(c)
            group = planned.get(cid, "idle")
            # Safeguard: ensure group is allowed (should match group_ids)
            # If a protecting group was constructed for a field that may not be present in group_ids (e.g., field with zero threat),
            # these groups are only expected for fields with threat>0 so this should be fine. Otherwise fallback to idle.
            if group not in group_ids:
                # fallback to idle
                group = "idle"
            environment.assign_group(c, group)
            # Update persistence state (we commanded this group)
            last = self.prev_assigned.get(cid)
            self.prev_assigned[cid] = group
            # update streak counter based on commanded group and previously commanded group
            if last == group:
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0