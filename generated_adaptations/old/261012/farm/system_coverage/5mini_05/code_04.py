from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        1. Sort threatened fields by descending threat_level (tie-break by id).
        2. For the top field: select the closest drones (among all drones) to fully protect it.
           This enforces the requirement that the highest-threat field is fully protected with the closest drones.
        3. For remaining fields (in descending threat order): keep any committed drones for that field
           (protecting or moving_to_field) if they're still available, and then add closest available drones
           until full protection is achieved or drones are exhausted.
        4. All unassigned drones are set to "idle".
        5. Explicitly assign every drone to exactly one group.
        """
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist2(loc_x, loc_y, cx, cy):
            dx = loc_x - cx
            dy = loc_y - cy
            return dx * dx + dy * dy

        # List of fields with positive threat
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats: all drones idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by descending threat, tie-break by id (string) for determinism
        threatened.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Prepare component list and maps
        comps = list(components)
        comp_by_id = {id(c): c for c in comps}

        # Track assignment decisions by component id (will assign at end)
        assignment = {}

        # Helper to pick closest N drones from a list of candidate components
        def pick_closest(candidates, cx, cy, n):
            cand_with_dist = []
            for c in candidates:
                try:
                    lx = getattr(c.location, "x", 0)
                    ly = getattr(c.location, "y", 0)
                    d2 = dist2(lx, ly, cx, cy)
                except Exception:
                    d2 = float("inf")
                cand_with_dist.append((d2, c))
            cand_with_dist.sort(key=lambda t: t[0])
            return [c for (_, c) in cand_with_dist[:n]]

        # Available set: components not yet assigned to a protecting group
        available_ids = set(comp_by_id.keys())

        # First, process the top-priority field: must be fully protected with closest drones
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        # If group not valid, fallback: make all idle (safe behavior)
        if top_group not in group_ids:
            for c in comps:
                environment.assign_group(c, "idle")
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        cx_top, cy_top = field_center(top_field)

        # Pick required_top closest drones among all components
        chosen_for_top = pick_closest(comps, cx_top, cy_top, required_top)

        # Assign them to top group
        for c in chosen_for_top:
            assignment[id(c)] = top_group
            if id(c) in available_ids:
                available_ids.remove(id(c))

        # Now process remaining fields in order (skip the top which is done)
        for field in threatened[1:]:
            group_name = f"protecting {field.id}"
            # If group not valid, skip protecting this field (drones remain available / idle)
            if group_name not in group_ids:
                continue

            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            cx, cy = field_center(field)

            # Identify committed drones for this field that are still available
            committed = []
            for cid in list(available_ids):
                c = comp_by_id[cid]
                if getattr(c, "target_id", None) == field.id and getattr(c, "state", None) in ("protecting", "moving_to_field"):
                    committed.append(c)

            # Keep committed drones assigned here (they remain available only if not taken earlier)
            for c in committed:
                assignment[id(c)] = group_name
                available_ids.discard(id(c))

            still_needed = max(0, required - len(committed))
            if still_needed == 0:
                continue

            # From remaining available drones (not yet assigned), pick closest still_needed
            remaining_candidates = [comp_by_id[cid] for cid in available_ids]
            selected = pick_closest(remaining_candidates, cx, cy, still_needed)
            for c in selected:
                assignment[id(c)] = group_name
                available_ids.discard(id(c))

        # Finally, any unassigned drones -> idle
        for cid in list(available_ids):
            c = comp_by_id[cid]
            assignment[cid] = "idle"

        # Make sure every component gets an assignment; if any missing, default to idle
        for c in comps:
            gid = assignment.get(id(c), "idle")
            if gid not in group_ids:
                # Safety: if target group is invalid, fall back to idle
                gid = "idle"
            environment.assign_group(c, gid)