from generated_adaptations.base_classes import farm as base

class SmartFarmAdaptation(base.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If there are no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Map field id to field object for quick access
        field_by_id = {getattr(f, "id"): f for f in threat_fields}
        threat_ids = set(field_by_id.keys())

        # Compute current number of drones protecting each field
        current_protect_count = {fid: 0 for fid in threat_ids}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_protect_count:
                    current_protect_count[tid] = current_protect_count.get(tid, 0) + 1

        # Fields that are already fully protected
        fully_protected_ids = set()
        for fid, f in field_by_id.items():
            required = getattr(f, "drones_for_full_protection", 0)
            if required > 0 and current_protect_count.get(fid, 0) >= required:
                fully_protected_ids.add(fid)

        # Step 1: Preserve current protections where applicable; idle others
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in threat_ids:
                    environment.assign_group(c, f"protecting {tid}")
                else:
                    environment.assign_group(c, "idle")
            else:
                environment.assign_group(c, "idle")

        # Step 2: Build remaining needs for fields not yet fully protected
        rem = {}      # field_id -> remaining drones needed
        centers = {}  # field_id -> (cx, cy)
        for fid, f in field_by_id.items():
            if fid in fully_protected_ids:
                continue
            required = getattr(f, "drones_for_full_protection", 0)
            if required <= 0:
                continue
            current = current_protect_count.get(fid, 0)
            remaining = max(0, int(required) - int(current))
            if remaining > 0:
                rem[fid] = remaining
                cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
                cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
                centers[fid] = (cx, cy)

        # If nothing to do, finish
        if not rem:
            return

        # Step 3: Collect idle drones as candidates for allocation
        spare = [c for c in components if getattr(c, "state", None) == "idle"]

        if not spare:
            return

        # Step 4: Allocate idle drones to fields in descending threat order
        threat_sorted = sorted(threat_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for f in threat_sorted:
            fid = getattr(f, "id")
            if fid not in rem:
                continue
            to_fill = rem[fid]
            if to_fill <= 0:
                continue
            if not spare:
                break

            cx, cy = centers[fid]

            # Sort spare by distance to the field center (closest first)
            def dist2_to_center(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return dx*dx + dy*dy

            spare.sort(key=dist2_to_center)

            take = min(to_fill, len(spare))
            for i in range(take):
                d = spare[i]
                environment.assign_group(d, f"protecting {fid}")
            # Remove allocated drones from spare
            spare = spare[take:]

            rem[fid] -= take
            if rem[fid] <= 0:
                del rem[fid]

        # Any remaining spare drones stay idle (already assigned)