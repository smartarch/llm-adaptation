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

        # Helper to determine a drone's current group
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                return f"protecting {d.target_id}"
            return "idle"

        # Precompute field centers and required drones for full protection
        field_center = {}
        field_required = {}
        for f in threatening_fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_center[f.id] = (cx, cy)
            req = int(getattr(f, "drones_for_full_protection", 1))
            field_required[f.id] = max(1, req)

        # Current protection counts and deficits
        protect_count = {f.id: 0 for f in threatening_fields}
        for d in components:
            grp = current_group(d)
            if grp.startswith("protecting "):
                fid = grp.split(" ", 1)[1]
                if fid in protect_count:
                    protect_count[fid] += 1

        deficits = {}
        for f in threatening_fields:
            fid = f.id
            deficits[fid] = max(0, field_required[fid] - protect_count.get(fid, 0))

        # Drones to move: map drone -> target field id
        moves = {}

        # Fields currently needing protection (deficit fields)
        deficit_fields = {f.id for f in threatening_fields if deficits.get(f.id, 0) > 0}
        # If there are deficits, try to fill them
        for f in threatening_fields:
            fid = f.id
            need = deficits.get(fid, 0)
            if need <= 0:
                continue

            cx, cy = field_center[fid]

            # Build candidate lists:
            # - no_deficit_candidates: drones idle or protecting a deficit field
            # - deficit_candidates: drones protecting a deficit field (fallback pool)
            no_deficit_candidates = []
            deficit_candidates = []

            for d in components:
                cur = current_group(d)
                if cur == f"protecting {fid}":
                    continue  # already protecting this field

                dist2 = float("inf")
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0) - cx
                    dy = getattr(loc, "y", 0) - cy
                    dist2 = dx*dx + dy*dy

                if cur == "idle":
                    no_deficit_candidates.append((dist2, d))
                elif cur.startswith("protecting "):
                    held_fid = cur.split(" ", 1)[1]
                    if held_fid in deficit_fields:
                        deficit_candidates.append((dist2, d))
                    # else: protecting a non-deficit field -> do not pull from here
                else:
                    # Treat other states (e.g., moving_to_field) conservatively:
                    # allow pulling only if considered as idle-like
                    no_deficit_candidates.append((dist2, d))

            # Sort by distance
            no_deficit_candidates.sort(key=lambda t: t[0])
            deficit_candidates.sort(key=lambda t: t[0])

            picked = []
            # First take from no_deficit_candidates (prefer not moving away from protected deficits)
            for _, drone in no_deficit_candidates:
                if len(picked) >= need:
                    break
                picked.append(drone)

            # If still need, take from deficit_candidates (last resort)
            if len(picked) < need:
                for _, drone in deficit_candidates:
                    if drone in picked:
                        continue
                    picked.append(drone)
                    if len(picked) >= need:
                        break

            # Assign picked drones to this field
            for drone in picked[:max(0, need)]:
                moves[drone] = fid
                deficits[fid] -= 1

            # Update deficit set for subsequent fields
            deficit_fields = {fid2 for fid2, val in deficits.items() if val > 0}

        # Final assignment: assign each drone to its final group
        for d in components:
            if d in moves:
                target_group = f"protecting {moves[d]}"
            else:
                target_group = current_group(d)

            if target_group not in group_ids:
                target_group = "idle" if "idle" in group_ids else group_ids[0]

            environment.assign_group(d, target_group)