from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components: List[object], environment, group_ids, step: int):
        """
        Improved strategy:
        - Always fully protect the field with highest threat_level using closest drones (keep committed).
        - Then try to fully protect other fields (by descending threat) using remaining drones.
        - If drones remain, assign them to partially protect the next-most-important field.
        - Prefer reassigning idle -> moving_to_field -> protecting (minimize disruption).
        """
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, field):
            cx, cy = field_center(field)
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy)

        drones = list(components)
        # If no drones, nothing to assign
        if not drones:
            return

        # Gather fields with positive threat
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        # If no threats, assign all to idle
        if not fields:
            for d in drones:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
            return

        # Sort fields by threat desc, tie-break by id for determinism
        fields.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)

        # Helper: get committed drones for a given field from a given pool
        def committed_for_field(drone_pool, field):
            committed = []
            for d in drone_pool:
                if getattr(d, "target_id", None) == field.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                    committed.append(d)
            return committed

        # Selection priority function for candidate drones relative to a field:
        # lower tuple sorts earlier: (priority_rank, distance, tiebreaker)
        def selection_key(drone, field):
            state = getattr(drone, "state", "")
            if state == "idle":
                pr = 0
            elif state == "moving_to_field":
                pr = 1
            else:  # protecting
                pr = 2
            return (pr, dist(drone, field), id(drone))

        # Keep track of assignments (set of drones assigned to protecting groups)
        assigned_protecting = {}  # field.id -> list of drones
        assigned_drones = set()   # drones already assigned (objects)

        # Step 1: Ensure the top field is fully protected
        top_field = fields[0]
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        top_required = max(0, min(top_required, len(drones)))

        # Get committed drones for top_field from full drone pool
        top_committed = committed_for_field(drones, top_field)
        # Sort committed deterministically by selection key (so result deterministic)
        top_committed.sort(key=lambda d: selection_key(d, top_field))
        selected_top = list(top_committed)

        # If more needed, pick from remaining drones using selection_key
        need = max(0, top_required - len(selected_top))
        if need > 0:
            # candidates are drones not already committed to top_field
            candidates = [d for d in drones if d not in selected_top]
            candidates.sort(key=lambda d: selection_key(d, top_field))
            for d in candidates[:need]:
                selected_top.append(d)

        # Mark selected_top as assigned
        assigned_protecting[top_field.id] = selected_top
        for d in selected_top:
            assigned_drones.add(d)

        # Step 2: Try to fully protect other fields using remaining drones
        remaining_drones = [d for d in drones if d not in assigned_drones]

        # Iterate remaining fields (excluding top) by descending threat
        for field in fields[1:]:
            required = int(getattr(field, "drones_for_full_protection", 0))
            required = max(0, min(required, len(drones)))  # cap
            if required == 0:
                continue

            # committed among remaining_drones
            committed = committed_for_field(remaining_drones, field)
            committed.sort(key=lambda d: selection_key(d, field))
            selected = list(committed)

            need_field = max(0, required - len(selected))
            if need_field > 0:
                # pick additional from remaining_drones excluding already selected
                candidates = [d for d in remaining_drones if d not in selected]
                candidates.sort(key=lambda d: selection_key(d, field))
                # select up to need_field
                for d in candidates[:need_field]:
                    selected.append(d)

            # If we managed to get any drones for this field, assign them (we aim for full protection)
            if selected:
                assigned_protecting[field.id] = selected
                for d in selected:
                    assigned_drones.add(d)
                # update remaining_drones
                remaining_drones = [d for d in drones if d not in assigned_drones]
            # continue to next field

        # Step 3: If drones remain, consider giving them as a partial protection to the highest-threat remaining field
        remaining_drones = [d for d in drones if d not in assigned_drones]
        if remaining_drones:
            # Find the best target among fields (prefer highest threat excluding top_field if already handled)
            # Candidate fields are those with threat>0; choose the one with highest threat that isn't already fully protected
            best_field = None
            for field in fields:
                # Determine currently assigned count (including those we assigned earlier)
                assigned_count = len(assigned_protecting.get(field.id, []))
                full_needed = int(getattr(field, "drones_for_full_protection", 0))
                if assigned_count < full_needed:
                    best_field = field
                    break
            # If none found (all fields fully protected), we can leave remaining drones idle (or keep them hovering)
            if best_field:
                # Assign all remaining drones to that field (partial help)
                # But be mindful to prefer drones that minimize disruption — remaining_drones already represent those not assigned
                # Sort remaining_drones by selection_key to be deterministic
                remaining_drones.sort(key=lambda d: selection_key(d, best_field))
                # Add them to assigned_protecting[best_field.id] (even if not enough for full protection)
                prev = assigned_protecting.get(best_field.id, [])
                assigned_protecting[best_field.id] = prev + remaining_drones
                for d in remaining_drones:
                    assigned_drones.add(d)
                remaining_drones = []

        # Final assignment: assign protecting groups for each field we prepared, others to idle
        # Assign groups for each drone exactly once
        # Validate group names; use "idle" group for idle assignment
        idle_group = "idle"
        for d in drones:
            # find if this drone is in assigned_protecting for some field
            assigned_group = None
            for fid, dlist in assigned_protecting.items():
                if d in dlist:
                    candidate_group = f"protecting {fid}"
                    if candidate_group in group_ids:
                        assigned_group = candidate_group
                    else:
                        # fallback: if protecting group name not present (shouldn't happen), skip
                        assigned_group = None
                    break
            if assigned_group:
                environment.assign_group(d, assigned_group)
            else:
                # assign idle if available, else fallback to first group_id
                if idle_group in group_ids:
                    environment.assign_group(d, idle_group)
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
                else:
                    # no group ids at all (unlikely), do nothing
                    pass