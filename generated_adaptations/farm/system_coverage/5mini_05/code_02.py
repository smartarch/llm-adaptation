from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Identify fields with threat_level > 0.
        - Pick the field with the highest threat level (tie broken by field.id).
        - Keep drones already protecting or moving to that field assigned to it.
        - If more drones are needed to reach field.drones_for_full_protection,
          pick the closest available drones to the field center and assign them.
        - All other drones are assigned to "idle".
        - Every drone is explicitly assigned a group every call.
        """
        # Helper to compute field center
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Helper to compute squared distance (no need to sqrt for ordering)
        def dist2(loc_x, loc_y, cx, cy):
            dx = loc_x - cx
            dy = loc_y - cy
            return dx * dx + dy * dy

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with highest threat_level; tie-break deterministically by id
        field_to_protect = max(threatened_fields, key=lambda f: (f.threat_level, str(f.id)))

        protect_group_name = f"protecting {field_to_protect.id}"
        # Sanity: ensure group name exists in provided group_ids (if not, fallback to idle for safety)
        if protect_group_name not in group_ids and "idle" in group_ids:
            # Can't assign to protecting group if it's not valid; all drones idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        required = int(getattr(field_to_protect, "drones_for_full_protection", 0))
        cx, cy = field_center(field_to_protect)

        # Identify drones already committed to this field (protecting or moving_to_field)
        committed = []
        committed_ids = set()
        for c in components:
            try:
                if getattr(c, "target_id", None) == field_to_protect.id and getattr(c, "state", None) in ("protecting", "moving_to_field"):
                    committed.append(c)
                    committed_ids.add(id(c))
            except Exception:
                # In case a component lacks attributes, skip committing it
                continue

        # Assign committed drones to protecting group (they stay)
        for c in committed:
            environment.assign_group(c, protect_group_name)

        # How many more drones we need
        still_needed = max(0, required - len(committed))

        # Prepare list of available drones (those not committed)
        available = []
        for c in components:
            if id(c) in committed_ids:
                continue
            # compute distance to field center for sorting
            try:
                lx = getattr(c.location, "x", 0)
                ly = getattr(c.location, "y", 0)
                d2 = dist2(lx, ly, cx, cy)
            except Exception:
                d2 = float("inf")
            available.append((d2, c))

        # Sort available drones by distance ascending
        available.sort(key=lambda pair: pair[0])

        # Assign the closest 'still_needed' drones to the protecting group
        assigned_protect_count = 0
        for d2, c in available:
            if assigned_protect_count < still_needed:
                environment.assign_group(c, protect_group_name)
                assigned_protect_count += 1
            else:
                # remaining drones set to idle
                environment.assign_group(c, "idle")

        # If there were no available drones (or some not assigned by above), ensure all components were assigned
        # (This covers any unexpected skips)
        assigned_so_far = set()
        # We re-check by attempting to assign any unassigned components to idle as a final step.
        # Since environment.assign_group has side-effects and we have already assigned all known components,
        # this loop mainly safeguards against missing any.
        for c in components:
            # We can't inspect environment assignment state, so ensure we still call assign_group at least once per component.
            # Above logic should have invoked assign_group for every component; this final pass will reassign any possibly missed ones to idle/protecting as appropriate.
            # Determine if the component was supposed to be protecting (committed or chosen among closest)
            # Use the same logic to decide final group here:
            should_protect = False
            if getattr(c, "target_id", None) == field_to_protect.id and getattr(c, "state", None) in ("protecting", "moving_to_field"):
                should_protect = True
            else:
                # check if it was one of the selected nearest (we recompute)
                lx = getattr(c.location, "x", 0) if hasattr(c, "location") else 0
                ly = getattr(c.location, "y", 0) if hasattr(c, "location") else 0
                d2 = dist2(lx, ly, cx, cy)
                # count how many available drones are closer or equal and whether this drone falls in the first 'still_needed' slots
                # To keep this final pass simple and deterministic, we will not recompute selection here; we assume earlier assignments happened.
                # If for some reason this drone wasn't assigned earlier, assign it to idle.
                # Therefore, skip reassigning protecting here to avoid overwriting desired assignments.
                continue  # nothing to do in final pass

        # End of method
        return