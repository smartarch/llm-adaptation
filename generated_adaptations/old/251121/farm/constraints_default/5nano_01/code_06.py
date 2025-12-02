from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, move all drones to idle (or first valid idle group)
        if not threatening_fields:
            for d in components:
                target = "idle" if "idle" in group_ids else group_ids[0]
                environment.assign_group(d, target)
            return

        # Sort threatening fields by threat level (highest first)
        threatening_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper to get current group for a drone
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                return f"protecting {d.target_id}"
            return "idle"

        # Compute center and required drones for each threatening field
        field_center = {}
        field_required = {}
        for f in threatening_fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_center[f.id] = (cx, cy)
            req = int(getattr(f, "drones_for_full_protection", 1))
            field_required[f.id] = max(1, req)

        # Current deficits for each field
        deficits = {}
        for f in threatening_fields:
            fid = f.id
            current = sum(1 for d in components if current_group(d) == f"protecting {fid}")
            deficits[fid] = max(0, field_required[fid] - current)
        deficit_ids = {fid for fid, val in deficits.items() if val > 0}

        moved = {}  # drone -> field_id it will protect
        # Fill deficits starting from highest-threat field
        for f in threatening_fields:
            fid = f.id
            need = deficits.get(fid, 0)
            if need <= 0:
                continue

            cx, cy = field_center[fid]
            candidates = []
            for d in components:
                if d in moved:
                    continue
                cur = current_group(d)
                # Do not pull drones from deficit fields
                if cur != "idle" and cur.split(" ", 1)[1] in deficit_ids:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dx = getattr(loc, "x", 0) - cx
                    dy = getattr(loc, "y", 0) - cy
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, d))
            candidates.sort(key=lambda t: t[0])

            for i in range(min(need, len(candidates))):
                d = candidates[i][1]
                moved[d] = fid
                deficits[fid] -= 1
                if deficits[fid] <= 0:
                    break
            deficit_ids = {fid2 for fid2, val in deficits.items() if val > 0}

        # Final assignment: assign each drone to its final group
        for d in components:
            if d in moved:
                target_group = f"protecting {moved[d]}"
            else:
                grp = current_group(d)
                if grp in group_ids:
                    target_group = grp
                else:
                    target_group = "idle" if "idle" in group_ids else group_ids[0]
            environment.assign_group(d, target_group)