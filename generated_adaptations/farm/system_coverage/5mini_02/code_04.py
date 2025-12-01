from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Fully protect the highest-threat field using the closest drones (including
          drones that may currently target other fields).
        - With remaining drones, attempt to fully protect additional fields in
          descending threat order (only full protection, no partial).
        - Keep drones already targeting a field if we decide to protect that field;
          otherwise drones can be reassigned.
        - Explicitly assign every drone to a group each call.
        """
        idle_group = "idle"
        available_groups = set(group_ids)

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_sq(x1, y1, x2, y2):
            dx = x1 - x2
            dy = y1 - y2
            return dx * dx + dy * dy

        # Filter threat fields (threat_level > 0) and sort by threat desc
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threats: assign all drones to idle (if available)
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute drone locations
        drone_locs = {}
        for comp in components:
            loc = getattr(comp, "location", None)
            if loc is None:
                drone_locs[comp] = (0.0, 0.0)
            else:
                drone_locs[comp] = (getattr(loc, "x", 0.0), getattr(loc, "y", 0.0))

        # Track assignments we will make: comp -> group_name
        assignment = {}

        # Helper to compute number of drones required for full protection
        def required_for(field):
            try:
                req = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                req = 0
            return max(0, req)

        # Pool of drones available for assignment (not yet assigned by our plan)
        remaining_drones = set(components)

        # Step 1: Protect the highest-threat field with closest drones
        top_field = threat_fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in available_groups:
            # If the protecting group is not present for the top field, fallback: idle everyone
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        req_top = required_for(top_field)
        cx_top, cy_top = field_center(top_field)

        # Drones already committed to the top field (by target_id)
        already_top = [c for c in components if getattr(c, "target_id", None) == top_field.id]
        selected_top = list(already_top)

        # If need more, pick closest drones from the pool excluding already_top
        if len(selected_top) < req_top:
            candidates = []
            for c in components:
                if c in selected_top:
                    continue
                x, y = drone_locs.get(c, (0.0, 0.0))
                d2 = dist_sq(x, y, cx_top, cy_top)
                candidates.append((d2, c))
            candidates.sort(key=lambda t: t[0])
            needed = req_top - len(selected_top)
            for i in range(min(needed, len(candidates))):
                selected_top.append(candidates[i][1])

        # Assign selected_top to top_group
        for c in selected_top:
            assignment[c] = top_group
            if c in remaining_drones:
                remaining_drones.remove(c)

        # Step 2: Try to protect additional fields (descending threat), skipping top_field
        for field in threat_fields[1:]:
            group_name = f"protecting {field.id}"
            if group_name not in available_groups:
                continue  # cannot assign to this group's name
            req = required_for(field)
            if req <= 0:
                continue

            # Drones already targeting this field (and still available)
            already = [c for c in components if getattr(c, "target_id", None) == field.id]
            # Keep only those that are still not assigned elsewhere by our plan
            already = [c for c in already if c in remaining_drones]

            if len(already) >= req:
                # Enough already committed drones: keep them assigned here
                for c in already[:req]:
                    assignment[c] = group_name
                    remaining_drones.discard(c)
                continue

            # Need more: see if remaining drones suffice to fill requirement
            needed = req - len(already)
            if len(remaining_drones) < needed:
                # Not enough drones left to fully protect this field; skip (better to keep them idle)
                continue

            # Choose closest remaining drones to this field center
            cx, cy = field_center(field)
            candidates = []
            for c in remaining_drones:
                x, y = drone_locs.get(c, (0.0, 0.0))
                d2 = dist_sq(x, y, cx, cy)
                candidates.append((d2, c))
            candidates.sort(key=lambda t: t[0])

            # Assign already ones first
            for c in already:
                assignment[c] = group_name
                remaining_drones.discard(c)

            # Then assign the closest needed from remaining pool
            for i in range(needed):
                c = candidates[i][1]
                if c in remaining_drones:
                    assignment[c] = group_name
                    remaining_drones.discard(c)

        # Step 3: Any drone left gets idle
        for c in list(remaining_drones):
            if idle_group in available_groups:
                assignment[c] = idle_group
            else:
                # If idle not available, assign them to the top group's protecting group as fallback
                assignment[c] = top_group

        # Finally, ensure every component is explicitly assigned (even if reassigning to same group)
        for comp in components:
            group = assignment.get(comp, idle_group if idle_group in available_groups else None)
            if group is None:
                # No valid group, try to assign to any protecting group from group_ids or default to first group_id
                if group_ids:
                    group = group_ids[0]
                else:
                    # Nothing to assign to; skip (shouldn't happen in valid environment)
                    continue
            environment.assign_group(comp, group)