from typing import List, Dict
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones to protecting groups:
        - Fully protect highest-threat field using closest drones; keep existing protectors there.
        - Then try to fully protect additional fields in descending threat order using available drones.
        - If fewer than half drones are protecting after that, as a last resort reassign some drones
          currently protecting low-threat fields to reach at least half protected.
        - Preserve protecting drones when possible to minimize churn.
        """
        # Helper: compute center for a field
        def field_center(field):
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0
            return cx, cy

        # Helper: distance from component to field center
        def dist_comp_field(comp, field_center_xy):
            loc = getattr(comp, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - field_center_xy[0]
            dy = getattr(loc, "y", 0) - field_center_xy[1]
            return math.hypot(dx, dy)

        # Fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # If no threatened fields, assign all to idle
        if not threat_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort fields by descending threat_level, deterministic tie-break by id
        threat_fields.sort(key=lambda f: (getattr(f, "threat_level", 0), str(getattr(f, "id", ""))), reverse=True)

        # Map field.id -> field object for quick lookup
        field_by_id = {f.id: f for f in threat_fields}

        # Build lists of components by their current protecting status
        # A drone is considered "currently protecting a threatened field" if state=="protecting" and its target field still has threat>0
        protecting_current: Dict[str, List] = {}
        for f in threat_fields:
            protecting_current[f.id] = []

        available = []  # comps not currently protecting a threatened field
        for comp in components:
            tgt = getattr(comp, "target_id", None)
            state = getattr(comp, "state", None)
            if state == "protecting" and tgt in field_by_id:
                protecting_current[tgt].append(comp)
            else:
                # idle, moving_to_field, or protecting a non-threat field -> considered available for reassignment
                available.append(comp)

        # We'll build assignment map: comp -> field_id (for protection) or None for idle
        assign_map: Dict[object, str] = {}

        total_drones = len(components)
        target_min_protect = (total_drones + 1) // 2  # aim for at least half (ceil)

        # First pass: try to fully protect fields in order without taking drones currently protecting other threatened fields
        # This keeps existing protectors in place.
        # Available pool will shrink as we assign drones.
        available_pool = available.copy()

        # For distance computation, precompute centers
        centers = {f.id: field_center(f) for f in threat_fields}

        protected_count = 0

        for field in threat_fields:
            fid = field.id
            req = int(getattr(field, "drones_for_full_protection", 0))
            # Drones already protecting this field (we will keep them)
            already = protecting_current.get(fid, []).copy()
            num_already = len(already)
            to_assign = []

            # Keep all existing protectors for this field (they remain assigned)
            for comp in already:
                assign_map[comp] = fid

            # If we already have enough
            if num_already >= req:
                protected_count += req  # field fully protected (we count only required number)
                # If there are extra protectors beyond required, keep them assigned as well (they are already counted once)
                continue

            # Need additional drones for this field
            needed = req - num_already
            # Sort available_pool by distance to this field
            center = centers[fid]
            available_pool.sort(key=lambda c: dist_comp_field(c, center))
            take = available_pool[:needed]
            for comp in take:
                assign_map[comp] = fid
            # Remove taken from available_pool
            available_pool = available_pool[len(take):]
            # Update protected_count
            protected_count += (num_already + len(take))

            # Stop early if no more available drones at all
            if not available_pool:
                # continue to next fields but no more available to assign without reassigning existing protectors
                continue

        # Second pass: if we still have fewer than target_min_protect, as a last resort reassign some drones
        # that are currently protecting lower-threat fields.
        if protected_count < target_min_protect:
            need_more = target_min_protect - protected_count
            # Build list of protectors that we could reassign, but prefer from lowest-threat fields
            # Only consider protectors from fields we've already considered and which are not the highest-priority protected ones
            # Build list of tuples (field_threat, field_id, comp)
            candidates_reassign = []
            for field in reversed(threat_fields):  # ascending threat (lowest first)
                fid = field.id
                # For each comp currently protecting this field:
                for comp in protecting_current.get(fid, []):
                    # If we already kept this comp assigned to its field in assign_map, consider it as candidate to move
                    # Otherwise, it may have been kept but we might still consider it
                    candidates_reassign.append((getattr(field, "threat_level", 0), fid, comp))
            # Sort candidates by (threat_level asc) already ensured by reversed iteration
            # We'll reassign up to need_more from these candidates
            # But we must ensure we don't remove protectors from a field that we intend to keep fully protected.
            # We'll pick candidates and reassign them to the highest-priority fields that still need drones.
            # Build list of fields that are not yet fully protected (based on assign_map)
            field_assigned_counts = {}
            for f in threat_fields:
                fid = f.id
                field_assigned_counts[fid] = 0
            for comp, fid in assign_map.items():
                # count assigned to that field
                field_assigned_counts[fid] = field_assigned_counts.get(fid, 0) + 1
            # Also include protectors we kept (those in protecting_current that were mapped)
            # Now determine fields that still need drones (desc by threat)
            fields_need = []
            for f in threat_fields:
                fid = f.id
                req = int(getattr(f, "drones_for_full_protection", 0))
                have = field_assigned_counts.get(fid, 0)
                if have < req:
                    fields_need.append((getattr(f, "threat_level", 0), fid, req - have))
            # sort fields_need by threat desc to assign reallocated protectors to higher-threat fields first
            fields_need.sort(key=lambda x: (x[0], str(x[1])), reverse=True)

            # Now iterate reassign candidates and assign them to fields_need
            reassign_idx = 0
            for _, fid_from, comp in candidates_reassign:
                if need_more <= 0:
                    break
                # Skip if comp was not actually kept assigned previously (i.e., assign_map may point to same field)
                # It's okay: we'll reassign only those currently assigned to their old field
                prev_target = getattr(comp, "target_id", None)
                # Make sure we're not removing the last protector needed to keep some field fully protected.
                # Only reassign if removing this comp won't cause its original field to drop below its required count,
                # unless it's the lowest-threat fields (we are iterating from low to high).
                # Compute current count for its original field
                orig_fid = prev_target if prev_target in field_assigned_counts else fid_from
                orig_req = int(getattr(field_by_id.get(orig_fid, None) or next((f for f in environment.fields if f.id==orig_fid), None), "drones_for_full_protection", 0))
                orig_have = field_assigned_counts.get(orig_fid, 0)
                # Only reassign if orig_have > orig_req (we have surplus) or orig_fid is a lower-priority field (we accept reducing it)
                # To be conservative, allow reassigning if orig_have > max(0, orig_req - 1) i.e., don't drop it below req-1
                if orig_have <= max(0, orig_req - 1):
                    # don't reassign this one
                    continue
                # Find a field that needs drones (fields_need)
                if not fields_need:
                    break
                # Pick highest-priority field needing drones
                _, fid_to, need_amount = fields_need[0]
                # Do the reassignment: decrement orig count, increment dest count
                field_assigned_counts[orig_fid] = orig_have - 1
                field_assigned_counts[fid_to] = field_assigned_counts.get(fid_to, 0) + 1
                # Update fields_need entry
                if need_amount <= 1:
                    fields_need.pop(0)
                else:
                    fields_need[0] = (fields_need[0][0], fields_need[0][1], fields_need[0][2] - 1)
                # Update assign_map accordingly
                assign_map[comp] = fid_to
                need_more -= 1
                protected_count += 1

        # Finalize assignments: assign any remaining comps that were selected in assign_map to their protecting groups
        # All others go to idle
        # Ensure we only assign to valid group ids; if not present fallback to "idle"
        # Build set of valid protecting group names
        valid_protect_groups = set(group_ids)
        for comp in components:
            if comp in assign_map:
                fid = assign_map[comp]
                group_name = f"protecting {fid}"
                if group_name in valid_protect_groups:
                    environment.assign_group(comp, group_name)
                else:
                    # fallback
                    environment.assign_group(comp, "idle")
            else:
                # If the drone was previously protecting a threatened field and we didn't select it,
                # but its previous field still has threat>0, keep it there to reduce churn.
                prev_tgt = getattr(comp, "target_id", None)
                prev_state = getattr(comp, "state", None)
                if prev_state == "protecting" and prev_tgt in field_by_id:
                    group_name = f"protecting {prev_tgt}"
                    if group_name in valid_protect_groups:
                        environment.assign_group(comp, group_name)
                        continue
                # otherwise idle
                environment.assign_group(comp, "idle")