from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build a list of fields that have positive threat and need protection
        fields_with_threat = []
        for f in getattr(environment, "fields", []) or []:
            threat = getattr(f, "threat_level", 0)
            if threat is None:
                threat = 0
            if threat > 0:
                fields_with_threat.append(f)

        if not fields_with_threat:
            # No field needs protection now; nothing to rearrange.
            return

        # Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat,
                               key=lambda fld: getattr(fld, "threat_level", 0),
                               reverse=True)

        # Prepare centers and required drone counts per field
        field_center = {}
        field_required = {}
        field_by_id = {}
        for f in fields_sorted:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_center[f.id] = (cx, cy)
            # drones_for_full_protection should be an int-like value
            req = int(getattr(f, "drones_for_full_protection", 1))
            field_required[f.id] = max(1, req)
            field_by_id[f.id] = f

        # Track which drones we allocate in this pass (by object id)
        allocated = set()

        # For each field, allocate drones to reach full protection if needed
        for f in fields_sorted:
            current = 0
            # Count drones currently protecting this field
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id:
                    current += 1

            needed = max(0, field_required[f.id] - current)
            if needed == 0:
                continue  # already fully protected or no drones needed

            cx, cy = field_center[f.id]

            # Build candidate drones: those not currently protecting this field
            candidates = []
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id:
                    continue  # already protecting this field
                loc = getattr(d, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0) - cx
                dy = getattr(loc, "y", 0) - cy
                dist2 = dx*dx + dy*dy
                candidates.append((dist2, d))

            # Sort by distance to field center (closest first)
            candidates.sort(key=lambda t: t[0])

            # Assign up to 'needed' drones to this field
            to_assign = [pair[1] for pair in candidates[:needed]]
            for drone in to_assign:
                group_id = f"protecting {f.id}"
                # Only assign if the group name is a valid one
                if group_id in group_ids:
                    environment.assign_group(drone, group_id)
                    allocated.add(id(drone))
                else:
                    # If the group name isn't valid for some reason, skip reassigning this drone
                    pass

        # Note:
        # - Drones already protecting a field that doesn't need extra protection remain in their groups.
        # - Other drones are left as-is, which may be idle or moving to a field, depending on their current state.
        # - We do not forcefully move drones away from a fully protected field. This respects the rule of keeping existing protection when it is already sufficient.