from math import hypot, ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: field center
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        # Helper: distance between drone and field center
        def dist_to_field(comp, field):
            cx, cy = field_center(field)
            lx = getattr(comp.location, "x", 0.0)
            ly = getattr(comp.location, "y", 0.0)
            return hypot(lx - cx, ly - cy)

        # Prepare lists and maps
        num_drones = len(components)
        # fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # Nothing to protect; assign all drones to idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        # sort fields by threat desc, tie by id to be deterministic
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # bookkeeping for assignments: None means not assigned yet; will set group name
        assigned_group = {i: None for i in range(num_drones)}
        available = set(range(num_drones))  # indices of drones not yet permanently allocated

        # helper to pick nearest available drones to a field, with preference modes
        def pick_candidates_for_field(field, needed, prefer_non_protecting_first=True):
            picked = []
            if needed <= 0:
                return picked
            # create list of (index, comp, state, target) for available drones
            avail_list = []
            for i in available:
                comp = components[i]
                avail_list.append((i, comp, comp.state, comp.target_id))
            # compute distances
            avail_with_dist = []
            for i, comp, state, targ in avail_list:
                d = dist_to_field(comp, field)
                avail_with_dist.append((d, i, comp, state, targ))
            # sort by distance asc (closest first)
            avail_with_dist.sort(key=lambda x: (x[0], x[1]))

            # Strategy: first take drones already protecting this field
            for d, i, comp, state, targ in avail_with_dist:
                if state == "protecting" and targ == field.id and i in available:
                    picked.append(i)
                    available.discard(i)
                    if len(picked) >= needed:
                        return picked

            if prefer_non_protecting_first:
                # take drones not currently protecting any field (idle or moving)
                for d, i, comp, state, targ in avail_with_dist:
                    if i not in available:
                        continue
                    if state != "protecting":
                        picked.append(i)
                        available.discard(i)
                        if len(picked) >= needed:
                            return picked
                # finally, take drones currently protecting other fields (steal) if still needed
                for d, i, comp, state, targ in avail_with_dist:
                    if i not in available:
                        continue
                    # only remaining candidates will be protecting other fields
                    picked.append(i)
                    available.discard(i)
                    if len(picked) >= needed:
                        return picked
            else:
                # no preference: just take closest available
                for d, i, comp, state, targ in avail_with_dist:
                    if i not in available:
                        continue
                    picked.append(i)
                    available.discard(i)
                    if len(picked) >= needed:
                        return picked

            return picked

        # 1) Fully protect the top-priority field (most threatened) using closest drones
        top_field = threatened_fields[0]
        req_top = int(getattr(top_field, "drones_for_full_protection", 0))
        if req_top < 0:
            req_top = 0

        # Count currently protecting that top field (these we prefer to keep)
        current_protectors = []
        for idx, comp in enumerate(components):
            if comp.state == "protecting" and comp.target_id == top_field.id:
                current_protectors.append(idx)

        # First, reserve those current protectors (but don't remove from available yet;
        # pick_candidates_for_field will include them preferentially)
        # Use pick_candidates_for_field to pick up to req_top closest candidates with preference to keep existing
        needed_top = req_top
        picked_top = pick_candidates_for_field(top_field, needed_top, prefer_non_protecting_first=True)
        # assign them
        for i in picked_top:
            assigned_group[i] = f"protecting {top_field.id}"

        # 2) Try to fully protect additional fields in order of descending threat
        # For each, try to allocate required drones without breaking top field assignment (available has been updated)
        # Note: pick_candidates_for_field will honor already assigned (because they were removed from available)
        for field in threatened_fields[1:]:
            req = int(getattr(field, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            # If not enough drones left in available to meet req, skip for now (we keep them idle)
            # But we will later maybe assign partials to reach half-protection threshold.
            if len(available) < req:
                continue
            picked = pick_candidates_for_field(field, req, prefer_non_protecting_first=True)
            if len(picked) >= req:
                for i in picked:
                    assigned_group[i] = f"protecting {field.id}"
            else:
                # Not enough to fully protect; release any partially stolen picks back into available
                for i in picked:
                    # Only release if not already preassigned (shouldn't be)
                    if assigned_group.get(i) is None:
                        available.add(i)

        # Count number currently assigned to protection
        protected_count = sum(1 for v in assigned_group.values() if v is not None)

        # 3) Ensure at least half the drones are used for protection most of the time.
        # If we have fewer than half protecting, assign remaining drones to protect the highest-threat fields
        # (may lead to partial protection) until the "half" threshold is met or we run out of fields/drones.
        min_protect_needed = ceil(num_drones / 2)
        if protected_count < min_protect_needed:
            # build list of fields to consider in priority order (top to bottom)
            # but avoid reassigning top field beyond its full requirement
            # build current assigned counts per field
            assigned_counts = {}
            for field in threatened_fields:
                assigned_counts[field.id] = sum(1 for v in assigned_group.values() if v == f"protecting {field.id}")
            # for fields not in threatened_fields we don't consider
            # fill remaining available drones, going through fields by priority (we prefer the top field first but without exceeding its full)
            for field in threatened_fields:
                if protected_count >= min_protect_needed:
                    break
                max_for_field = int(getattr(field, "drones_for_full_protection", 0))
                already = assigned_counts.get(field.id, 0)
                can_add = max_for_field - already
                # If can_add is zero, we can't add more to this field
                if can_add <= 0:
                    continue
                # number to take to reach min_protect_needed or to fill this field
                need_to_reach = min(min_protect_needed - protected_count, can_add)
                # pick closest available drones (no special prefer)
                picked = pick_candidates_for_field(field, need_to_reach, prefer_non_protecting_first=False)
                # If not enough available to fill can_add but we still need to reach half, accept partial from available
                if picked:
                    for i in picked:
                        assigned_group[i] = f"protecting {field.id}"
                    protected_count = sum(1 for v in assigned_group.values() if v is not None)
                    assigned_counts[field.id] = sum(1 for v in assigned_group.values() if v == f"protecting {field.id}")

        # 4) Any remaining available drones -> idle
        for i in list(available):
            assigned_group[i] = "idle"
            available.discard(i)

        # Final safety: ensure every drone got assigned exactly one group
        for idx in range(num_drones):
            group = assigned_group.get(idx)
            if group is None:
                # fallback to idle
                group = "idle"
                assigned_group[idx] = group
            # Ensure the group id is valid (should be provided in group_ids). If not, default to "idle".
            if group not in group_ids:
                # Try to map protecting {id} if possible, else idle
                if group.startswith("protecting "):
                    # if group missing, fallback to idle
                    group = "idle"
                    assigned_group[idx] = group

            # perform the assignment
            environment.assign_group(components[idx], assigned_group[idx])