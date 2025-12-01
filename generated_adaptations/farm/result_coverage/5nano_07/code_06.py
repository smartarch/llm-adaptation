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

        # First, ensure we preserve protection for drones already protecting non-fully-protected fields
        # and re-assign drones to their current protecting groups as a baseline.
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in threat_ids:
                    environment.assign_group(c, f"protecting {tid}")
                else:
                    # Target is not a threat field; keep protecting it if possible, else idle
                    environment.assign_group(c, "idle")
            else:
                # Idle drones will be considered as spare
                environment.assign_group(c, "idle")

        # Build remaining needs for fields not yet fully protected
        rem = {}  # field_id -> remaining drones needed
        centers = {}
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

        # If nothing more to do, finish
        if not rem:
            return

        # Collect idle drones as spare pool
        spare = [c for c in components if getattr(c, "state", None) == "idle"]

        # Greedily allocate spare drones to fields with remaining needs
        for c in spare:
            if not rem:
                break
            # Find best field for this drone
            best_fid = None
            best_score = 0.0
            # Drone location
            loc = getattr(c, "location", None)
            dx0 = getattr(loc, "x", 0.0)
            dy0 = getattr(loc, "y", 0.0)
            for fid, r in rem.items():
                if r <= 0:
                    continue
                cx, cy = centers[fid]
                # distance to field center
                dx = dx0 - cx
                dy = dy0 - cy
                dist = (dx*dx + dy*dy) ** 0.5
                threat = getattr(field_by_id[fid], "threat_level", 0.0)
                score = (threat / max(1, r)) / (1.0 + dist)
                if score > best_score:
                    best_score = score
                    best_fid = fid
            if best_fid is None:
                environment.assign_group(c, "idle")
            else:
                environment.assign_group(c, f"protecting {best_fid}")
                rem[best_fid] -= 1
                if rem[best_fid] <= 0:
                    del rem[best_fid]
                    # If a field becomes fully protected, no longer consider it
        # Any remaining idle drones stay idle (already assigned)