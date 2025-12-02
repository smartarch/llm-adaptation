from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        threat_fields = []
        for f in environment.fields:
            if getattr(f, "threat_level", 0) > 0:
                threat_fields.append(f)
        # If no threats, set all drones to idle (fallback)
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else None)
        if not threat_fields or idle_group is None:
            for d in components:
                if idle_group is not None:
                    environment.assign_group(d, idle_group)
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda fld: getattr(fld, "threat_level", 0), reverse=True)

        # Keep track of drones still available for assignment
        available = list(components)
        # Track which drones have been assigned (useful if we later want to do extra checks)
        # assigned_groups = {}

        # Helper to compute field center
        def field_center(fld):
            cx = (fld.left + fld.right) / 2.0
            cy = (fld.top + fld.bottom) / 2.0
            return cx, cy

        # For each field in priority order, try to allocate drones
        for fld in threat_fields:
            group_name = f"protecting {fld.id}"
            if group_name not in group_ids:
                # Skip if we can't assign to this group's name
                continue

            drones_needed = int(getattr(fld, "drones_for_full_protection", 0) or 0)
            if drones_needed <= 0:
                # If no explicit drone count is required for full protection, skip
                continue

            if not available:
                break

            cx, cy = field_center(fld)

            # Distances to the field center for all currently available drones
            dist_list = []
            for d in available:
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float('inf')
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist2 = dx * dx + dy * dy
                dist_list.append((dist2, d))

            dist_list.sort(key=lambda t: t[0])

            # Decide how many to assign to this field
            if drones_needed > len(dist_list):
                n_assign = len(dist_list)
            else:
                n_assign = drones_needed

            # Assign closest drones to this field's protecting group
            for i in range(n_assign):
                drone = dist_list[i][1]
                if group_name in group_ids:
                    environment.assign_group(drone, group_name)
                else:
                    # Fallback to idle if the protecting group isn't valid
                    if idle_group is not None:
                        environment.assign_group(drone, idle_group)
                # Remove from available
                if drone in available:
                    available.remove(drone)

        # After attempting to fully protect fields, if any drones remain, allocate them as partial protection or idle
        # We prefer leaving them idle to avoid unnecessary movement unless there is a next best field to partially protect.
        # If there is remaining threat fields we could allocate these as partial, but for simplicity we place them idle here.
        for d in available:
            if idle_group is not None:
                environment.assign_group(d, idle_group)