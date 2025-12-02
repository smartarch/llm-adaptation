from typing import List, Dict, Set
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones so that:
        - The most threatened field is always fully protected using the closest drones (may reassign others).
        - Then try to fully protect other fields while preserving existing protectors and using available drones.
        - If fewer than half drones are protecting, do a last-resort reassignment from lowest-threat fields (not top)
          to reach at least half protected.
        """
        def field_center(field):
            return ((getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0,
                    (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0)

        def dist(loc, center_xy):
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - center_xy[0]
            dy = getattr(loc, "y", 0) - center_xy[1]
            return math.hypot(dx, dy)

        # Gather threatened fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # Nothing to protect
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort fields by descending threat_level, deterministically tie-break by id
        threat_fields.sort(key=lambda f: (getattr(f, "threat_level", 0), str(getattr(f, "id", ""))), reverse=True)
        top_field = threat_fields[0]

        # Precompute centers
        centers = {f.id: field_center(f) for f in threat_fields}

        # Current protectors by field (only for threatened fields)
        protecting_current: Dict[str, List] = {f.id: [] for f in threat_fields}
        for comp in components:
            if getattr(comp, "state", None) == "protecting":
                tgt = getattr(comp, "target_id", None)
                if tgt in protecting_current:
                    protecting_current[tgt].append(comp)

        # Assignment map comp->field_id
        assign_map: Dict[object, str] = {}

        # STEP 1: Fully protect top_field with closest drones (allow reassigning any drones if needed)
        top_req = int(getattr(top_field, "drones_for_full_protection", 0))
        top_center = centers[top_field.id]

        # Start with drones already protecting the top field
        selected_top: List = protecting_current.get(top_field.id, []).copy()
        selected_top_set: Set = set(selected_top)

        # If still need more, sort all other drones by distance to top and pick nearest
        if len(selected_top) < top_req:
            # Prepare list of remaining drones sorted by distance (including those protecting other fields)
            remaining = [c for c in components if c not in selected_top_set]
            remaining.sort(key=lambda c: dist(getattr(c, "location", None), top_center))
            need = top_req - len(selected_top)
            for c in remaining[:need]:
                selected_top.append(c)
                selected_top_set.add(c)

        # Assign selected top protectors
        for c in selected_top:
            assign_map[c] = top_field.id

        # Remove those selected from any other current protector lists
        for fid, lst in protecting_current.items():
            if fid == top_field.id:
                continue
            protecting_current[fid] = [c for c in lst if c not in selected_top_set]

        # Build a pool of available drones for assigning to other fields:
        # Prefer drones that are not currently protecting any threatened field (idle or moving or protecting non-threat).
        current_protectors_all = set()
        for lst in protecting_current.values():
            current_protectors_all.update(lst)
        # Also include components that were protecting top (now assigned) are already removed
        available_pool = [c for c in components if c not in selected_top_set and c not in current_protectors_all]

        # For distance sorting later, we will sort slices as needed.

        # STEP 2: For remaining fields (descending threat), keep existing protectors, then use available_pool (nearest) to fill
        field_assigned_counts: Dict[str, int] = {}
        for f in threat_fields:
            fid = f.id
            req = int(getattr(f, "drones_for_full_protection", 0))
            if fid == top_field.id:
                # top already assigned
                field_assigned_counts[fid] = min(top_req, sum(1 for c in selected_top))
                continue
            kept = protecting_current.get(fid, []).copy()
            # Keep them assigned
            for c in kept:
                assign_map[c] = fid
            have = len(kept)
            need = max(0, req - have)
            if need > 0 and available_pool:
                # sort available by distance to this field
                avail_sorted = sorted(available_pool, key=lambda c: dist(getattr(c, "location", None), centers[fid]))
                take = avail_sorted[:need]
                for c in take:
                    assign_map[c] = fid
                # remove taken from available_pool
                taken_set = set(take)
                available_pool = [c for c in available_pool if c not in taken_set]
                have += len(take)
            field_assigned_counts[fid] = have

        # Compute number protecting (count assigned to any protecting group)
        protected_count = sum(min(int(getattr(next((ff for ff in threat_fields if ff.id==fid), None), "drones_for_full_protection", 0)) if False else field_assigned_counts.get(fid, 0), 10**9) for fid in field_assigned_counts)

        # STEP 3: Ensure at least half drones are protecting (last-resort), do not reduce top_field assignments
        total_drones = len(components)
        target_min_protect = (total_drones + 1) // 2  # ceil half
        if protected_count < target_min_protect:
            need_more = target_min_protect - protected_count
            # Candidates to reassign: first from available_pool (these are not protecting threatened fields but may be idle/moving) - already used above
            # If available_pool depleted, consider reassigning protectors from lowest-threat fields (excluding top_field),
            # preferring those from the lowest-threat fields.
            # Build list of protector comps from other fields sorted by ascending field threat
            reclaim_candidates = []
            for f in reversed(threat_fields):  # low to high threat
                if f.id == top_field.id:
                    continue
                for c in protecting_current.get(f.id, []):
                    # only consider if this comp wasn't already assigned elsewhere (it currently mapped to this field)
                    # and is not already in assign_map assigned to something else
                    if c not in assign_map or assign_map.get(c) == f.id:
                        reclaim_candidates.append((getattr(f, "threat_level", 0), f.id, c))
            # sort by threat asc then id
            reclaim_candidates.sort(key=lambda x: (x[0], str(x[1])))

            # Fields that still need drones (desc by threat, excluding top which is full)
            fields_need = []
            for f in threat_fields:
                if f.id == top_field.id:
                    continue
                req = int(getattr(f, "drones_for_full_protection", 0))
                have = field_assigned_counts.get(f.id, 0)
                if have < req:
                    fields_need.append((getattr(f, "threat_level", 0), f.id, req - have))
            fields_need.sort(key=lambda x: (x[0], str(x[1])), reverse=True)

            # First use any remaining available_pool drones (they are good)
            while need_more > 0 and available_pool:
                c = available_pool.pop(0)
                # Choose the highest-priority field that still needs drones, else assign to idle? Prefer assigning to any (we will assign to the most threatened needing field)
                if fields_need:
                    _, fid_to, need_amt = fields_need[0]
                    assign_map[c] = fid_to
                    field_assigned_counts[fid_to] = field_assigned_counts.get(fid_to, 0) + 1
                    if need_amt <= 1:
                        fields_need.pop(0)
                    else:
                        fields_need[0] = (fields_need[0][0], fields_need[0][1], fields_need[0][2] - 1)
                else:
                    # No field needs drones; assign to any non-top field with lowest threat to increase utilization
                    # pick lowest-threat field
                    chosen_field = None
                    for ff in reversed(threat_fields):
                        if ff.id == top_field.id:
                            continue
                        chosen_field = ff.id
                        break
                    if chosen_field is not None:
                        assign_map[c] = chosen_field
                        field_assigned_counts[chosen_field] = field_assigned_counts.get(chosen_field, 0) + 1
                need_more -= 1
                protected_count += 1

            # If still need more, start reclaiming protectors from lowest-threat fields
            ri = 0
            while need_more > 0 and ri < len(reclaim_candidates):
                _, fid_from, comp = reclaim_candidates[ri]
                ri += 1
                # Skip if comp already reassigned or comp assigned to top
                if comp in assign_map and assign_map[comp] == top_field.id:
                    continue
                # Do not take the last drone if that would make original field lose all protection — but we may be allowed to reduce them
                # Here we allow reclaiming but try to avoid reducing a field to below max(0, req-1)
                orig_req = int(getattr(next((ff for ff in threat_fields if ff.id==fid_from), None), "drones_for_full_protection", 0))
                orig_have = field_assigned_counts.get(fid_from, len(protecting_current.get(fid_from, [])))
                if orig_have <= max(0, orig_req - 1):
                    # skip this candidate to avoid overly weakening a field
                    continue
                # Assign this comp to the highest-threat field that still needs drones, or to any non-top field if none need
                if fields_need:
                    _, fid_to, need_amt = fields_need[0]
                    target_fid = fid_to
                    # update fields_need
                    if need_amt <= 1:
                        fields_need.pop(0)
                    else:
                        fields_need[0] = (fields_need[0][0], fields_need[0][1], fields_need[0][2] - 1)
                else:
                    # choose lowest-threat non-top field to increase utilization
                    target_fid = None
                    for ff in threat_fields[::-1]:
                        if ff.id != top_field.id:
                            target_fid = ff.id
                            break
                    if target_fid is None:
                        # no suitable target, stop
                        break
                # Reassign comp
                assign_map[comp] = target_fid
                # update counts
                field_assigned_counts[fid_from] = max(0, field_assigned_counts.get(fid_from, 0) - 1)
                field_assigned_counts[target_fid] = field_assigned_counts.get(target_fid, 0) + 1
                need_more -= 1
                protected_count += 1

        # FINAL: Do actual environment.assign_group for each component.
        valid_groups = set(group_ids)
        for comp in components:
            if comp in assign_map:
                gid = f"protecting {assign_map[comp]}"
                if gid in valid_groups:
                    environment.assign_group(comp, gid)
                else:
                    environment.assign_group(comp, "idle")
            else:
                # If drone was previously protecting a threatened field and we didn't select it for reassignment,
                # keep it where it was to reduce churn.
                prev_tgt = getattr(comp, "target_id", None)
                prev_state = getattr(comp, "state", None)
                if prev_state == "protecting" and prev_tgt in centers:
                    gid = f"protecting {prev_tgt}"
                    if gid in valid_groups:
                        environment.assign_group(comp, gid)
                        continue
                # otherwise idle
                environment.assign_group(comp, "idle")