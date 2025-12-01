from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved allocation:
        - Reserve drones that are already protecting fully-protected fields.
        - Ensure the highest-threat field (threat_level > 0) is fully protected using the closest available drones.
        - Greedily fully protect additional fields (by descending threat) using remaining drones (only if we can reach full protection).
        - Prefer drones already protecting/moving to a target when filling that target.
        - All other drones -> idle.
        """
        # Helpers
        def dist_to_point(drone, px, py):
            dx = getattr(drone.location, "x", 0) - px
            dy = getattr(drone.location, "y", 0) - py
            return hypot(dx, dy)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else idle_group

        # Gather threatened fields (threat_level > 0), sorted desc by threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats -> idle everyone
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Map to store field center coordinates
        field_centers = {}
        for f in fields_sorted:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_centers[f.id] = (cx, cy)

        comps = list(components)

        # Compute current protectors per field (drones with state "protecting" and matching target_id)
        protectors_by_field = {}
        for f in fields_sorted:
            protectors_by_field[f.id] = [c for c in comps
                                         if getattr(c, "state", None) == "protecting"
                                         and getattr(c, "target_id", None) == f.id]

        # Reserve drones that are already protecting a fully-protected field (keep them there)
        reserved = set()
        fully_protected_fields = set()
        for f in fields_sorted:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len(protectors_by_field.get(f.id, []))
            if required > 0 and cur >= required:
                # Field is fully protected; reserve its protectors
                fully_protected_fields.add(f.id)
                for c in protectors_by_field[f.id]:
                    reserved.add(c)

        # Available drones are those not reserved
        available = [c for c in comps if c not in reserved]

        # Assignment data structures
        assignment = {}  # comp -> group string
        # First, assign reserved protectors to their protecting groups
        for f in fields_sorted:
            if f.id in fully_protected_fields:
                grp = f"protecting {f.id}"
                if grp not in group_ids:
                    grp = idle_group
                for c in protectors_by_field.get(f.id, []):
                    assignment[c] = grp

        # Helper to allocate drones to a specific field (attempt to fully protect)
        def allocate_for_field(field, avail_list):
            """
            Try to fully protect 'field' using drones from avail_list.
            Returns (assigned_list, remaining_avail_list, success_bool)
            """
            grp_name = f"protecting {field.id}"
            if grp_name not in group_ids:
                return ([], avail_list, False)

            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                return ([], avail_list, False)

            # Count existing protectors and movers among available (we prefer them)
            protect_now = [c for c in avail_list
                           if getattr(c, "state", None) == "protecting"
                           and getattr(c, "target_id", None) == field.id]

            moving_to = [c for c in avail_list
                         if getattr(c, "state", None) == "moving_to_field"
                         and getattr(c, "target_id", None) == field.id
                         and c not in protect_now]

            assigned = list(protect_now) + list(moving_to)
            assigned_set = set(assigned)

            need = max(0, required - len(assigned))
            if need == 0:
                # Already satisfied among available drones
                # Remove assigned from avail and return success
                new_avail = [c for c in avail_list if c not in assigned_set]
                return (assigned, new_avail, True)

            # Remaining candidates are other available drones
            cx, cy = field_centers[field.id]
            others = [c for c in avail_list if c not in assigned_set]

            # Sort others by distance to field center
            others_sorted = sorted(others, key=lambda c: dist_to_point(c, cx, cy))

            if len(others_sorted) < need:
                # Not enough available to fully protect this field
                return ([], avail_list, False)

            chosen = others_sorted[:need]
            assigned.extend(chosen)
            new_avail = [c for c in avail_list if c not in set(assigned)]
            return (assigned, new_avail, True)

        # Step A: Ensure highest-threat field is fully protected.
        top_field = fields_sorted[0]
        # Make top field available set exclude reserved (we already built available)
        assigned_top, available_after_top, success_top = allocate_for_field(top_field, available)
        # If not successful, we must still try to enforce the rule: always fully protect highest-threat field.
        # As reserved only contains protectors of already fully protected fields, we can try again using all drones (except reserved),
        # but if allocation failed because protect_group missing we fallback to idle. However typical case should succeed.
        if not success_top:
            # Try a more flexible allocation allowing reclaiming drones that are currently protecting other non-fully fields:
            # (available already includes those); since allocate_for_field returned failure due to insufficient count, we cannot
            # fully protect top field; in this unlikely case, we will still pick nearest drones up to required (best-effort).
            # We'll take the nearest available drones to top_field center.
            cx, cy = field_centers[top_field.id]
            required = int(getattr(top_field, "drones_for_full_protection", 0))
            # Sort available by distance
            sorted_avail = sorted(available, key=lambda c: dist_to_point(c, cx, cy))
            chosen = sorted_avail[:required] if required > 0 else []
            assigned_top = chosen
            available_after_top = [c for c in available if c not in set(chosen)]
            # success_top remains False but we proceed with best-effort

        # Record assignments for top field
        protect_group_top = f"protecting {top_field.id}"
        if protect_group_top not in group_ids:
            protect_group_top = idle_group
        for c in assigned_top:
            assignment[c] = protect_group_top

        # Update available to remaining
        available = available_after_top

        # Step B: Greedily try to fully protect other fields in descending threat order (skip top_field and already fully protected)
        for f in fields_sorted[1:]:
            if f.id in fully_protected_fields:
                continue
            assigned, available, success = allocate_for_field(f, available)
            if success and assigned:
                grp = f"protecting {f.id}"
                if grp not in group_ids:
                    grp = idle_group
                for c in assigned:
                    assignment[c] = grp
            # If not successful, skip this field (do not do partial allocation)

        # Finally, assign all remaining drones (not reserved and not assigned) to idle.
        for c in comps:
            if c in assignment:
                # already set
                environment.assign_group(c, assignment[c])
            else:
                # For protected drones that were reserved earlier but not assigned (shouldn't happen), ensure they get their protecting group
                if c in reserved:
                    # Find its target id from current state (those were protecting)
                    tid = getattr(c, "target_id", None)
                    grp = f"protecting {tid}" if tid is not None else idle_group
                    if grp not in group_ids:
                        grp = idle_group
                    environment.assign_group(c, grp)
                else:
                    environment.assign_group(c, idle_group)