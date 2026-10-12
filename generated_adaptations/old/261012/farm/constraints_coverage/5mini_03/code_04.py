from math import hypot, ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that:
        - The field with highest threat_level (>0) is fully protected (use drones_for_full_protection).
        - Then assign additional drones to other threatened fields to ensure at least half of drones
          are assigned to some protecting group, preferring higher-threat fields and drones already
          targeting those fields.
        - Remaining drones are set to "idle".
        """
        # helper to safely assign a component to a group that exists in group_ids
        def assign_if_valid(comp, gid):
            if gid in group_ids:
                environment.assign_group(comp, gid)
            else:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                elif group_ids:
                    environment.assign_group(comp, group_ids[0])
                # else: nothing to do

        comps = list(components)
        total = len(comps)
        if total == 0:
            return

        # Candidate fields with positive threat
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, make all drones idle
        if not candidate_fields:
            for comp in comps:
                assign_if_valid(comp, "idle")
            return

        # Choose primary field: highest threat_level, tie-break by id for determinism
        primary = max(candidate_fields, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        primary_group = f"protecting {primary.id}"

        # Precompute field centers
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        primary_cx, primary_cy = field_center(primary)

        # Helper to distance from field center
        def dist_to_field(comp, cx, cy):
            lx = getattr(comp.location, "x", 0)
            ly = getattr(comp.location, "y", 0)
            return hypot(lx - cx, ly - cy)

        # Track assignments by id to avoid relying on component hashability
        assigned_group_by_id = {}
        assigned_ids = set()  # set of id(comp) assigned to protecting groups

        # Step 1: commit drones already targeting primary
        committed_primary = [c for c in comps if c.target_id == primary.id]
        for c in committed_primary:
            cid = id(c)
            assigned_group_by_id[cid] = primary_group
            assigned_ids.add(cid)

        # Step 2: select nearest drones to fill primary requirement
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))
        if required_primary < 0:
            required_primary = 0
        already_primary = len(committed_primary)
        need_primary = max(0, required_primary - already_primary)

        # Candidates for selection: those not already assigned to primary
        remaining_for_selection = [c for c in comps if id(c) not in assigned_ids]
        if need_primary > 0 and remaining_for_selection:
            others_with_dist = [(dist_to_field(c, primary_cx, primary_cy), c) for c in remaining_for_selection]
            others_with_dist.sort(key=lambda t: t[0])
            to_select = [c for (_, c) in others_with_dist[:need_primary]]
            for c in to_select:
                cid = id(c)
                assigned_group_by_id[cid] = primary_group
                assigned_ids.add(cid)

        # Count how many drones are protecting now
        protecting_count = len(assigned_ids)

        # Desired minimum protecting drones: at least half
        target_protect = ceil(total / 2)

        # Step 3: Assign drones to other threatened fields to reach target_protect
        # Sort other fields by threat desc, tie-break by id
        other_fields = [f for f in candidate_fields if f.id != primary.id]
        other_fields.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)

        # Remaining drones pool (not yet assigned to protecting groups)
        remaining_pool = [c for c in comps if id(c) not in assigned_ids]

        for field in other_fields:
            if protecting_count >= target_protect:
                break
            field_group = f"protecting {field.id}"
            cx, cy = field_center(field)

            # First, assign drones already targeting this field (from remaining_pool)
            already_targeting = [c for c in remaining_pool if c.target_id == field.id]
            for c in already_targeting:
                cid = id(c)
                assigned_group_by_id[cid] = field_group
                assigned_ids.add(cid)
                protecting_count += 1

            # Refresh remaining_pool
            remaining_pool = [c for c in remaining_pool if id(c) not in assigned_ids]
            if protecting_count >= target_protect:
                break

            # Determine how many more would fully protect this field
            required_field = int(getattr(field, "drones_for_full_protection", 0))
            if required_field < 0:
                required_field = 0
            # Count currently assigned for this field among those we just assigned
            currently_assigned_for_field = len(already_targeting)
            need_for_field = max(0, required_field - currently_assigned_for_field)

            # We'll assign up to need_for_field drones (or fewer if we only need enough to reach target_protect)
            # Choose closest drones from remaining_pool
            if remaining_pool and (need_for_field > 0):
                # compute distances
                pool_with_dist = [(dist_to_field(c, cx, cy), c) for c in remaining_pool]
                pool_with_dist.sort(key=lambda t: t[0])
                # how many to pick so we don't exceed target_protect
                max_can_take = min(len(pool_with_dist), need_for_field, target_protect - protecting_count)
                to_take = [c for (_, c) in pool_with_dist[:max_can_take]]
                for c in to_take:
                    cid = id(c)
                    assigned_group_by_id[cid] = field_group
                    assigned_ids.add(cid)
                    protecting_count += 1
                # refresh remaining pool
                remaining_pool = [c for c in remaining_pool if id(c) not in assigned_ids]

        # Step 4: If still below target_protect, assign remaining drones (closest) to protect primary (or highest-threat field)
        if protecting_count < target_protect:
            # remaining_pool updated
            remaining_pool = [c for c in comps if id(c) not in assigned_ids]
            if remaining_pool:
                # Use primary as fallback target (could also pick highest threat but primary is highest)
                # Sort by distance to primary
                pool_with_dist = [(dist_to_field(c, primary_cx, primary_cy), c) for c in remaining_pool]
                pool_with_dist.sort(key=lambda t: t[0])
                needed_more = target_protect - protecting_count
                for (_, c) in pool_with_dist[:needed_more]:
                    cid = id(c)
                    assigned_group_by_id[cid] = primary_group
                    assigned_ids.add(cid)
                    protecting_count += 1

        # Final assignment: assign groups to components; all assigned_groups -> protecting groups, others -> idle
        for c in comps:
            cid = id(c)
            if cid in assigned_group_by_id:
                assign_if_valid(c, assigned_group_by_id[cid])
            else:
                assign_if_valid(c, "idle")