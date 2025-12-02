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
        top_field = threatening_fields[0]

        # Helper to determine a drone's current group
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                return f"protecting {d.target_id}"
            return "idle"

        # Compute centers and required drones for full protection
        field_center = {}
        field_required = {}
        threat_by_id = {}
        for f in threatening_fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_center[f.id] = (cx, cy)
            field_required[f.id] = max(1, int(getattr(f, "drones_for_full_protection", 1)))
            threat_by_id[f.id] = getattr(f, "threat_level", 0)

        # Current protection counts per field
        protect_count = {f.id: 0 for f in threatening_fields}
        for d in components:
            grp = current_group(d)
            if grp.startswith("protecting "):
                fid = grp.split(" ", 1)[1]
                if fid in protect_count:
                    protect_count[fid] += 1

        # Deficits for each field
        deficits = {}
        for f in threatening_fields:
            deficits[f.id] = max(0, field_required[f.id] - protect_count.get(f.id, 0))

        # Drones to move: map drone -> field_id to protect
        moves = {}

        # Fields currently needing protection (deficit fields)
        deficit_fields = {f.id for f in threatening_fields if deficits.get(f.id, 0) > 0}

        # Fill deficits in descending threat order
        for f in threatening_fields:
            fid = f.id
            need = deficits.get(fid, 0)
            if need <= 0:
                continue

            cx, cy = field_center[fid]

            # Build candidate lists with priority:
            #  - 0: idle drones
            #  - 1: drones protecting fields with lower threat than current
            #  - 2: drones protecting fields with threat >= current (last resort)
            candidates = []
            for d in components:
                if d in moves:
                    continue
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
                    priority = 0
                elif cur.startswith("protecting "):
                    held_id = cur.split(" ", 1)[1]
                    held_threat = threat_by_id.get(held_id, 0)
                    cur_threat = threat_by_id.get(fid, getattr(f, "threat_level", 0))
                    # Prefer moving from lower-threat fields
                    priority = 1 if held_threat < cur_threat else 2
                else:
                    # Other states (e.g., moving_to_field) treated conservatively
                    priority = 2

                candidates.append((priority, dist2, d))

            # Sort by priority then distance
            candidates.sort(key=lambda t: (t[0], t[1]))

            picked = []
            for _, __, drone in candidates:
                if len(picked) >= need:
                    break
                picked.append(drone)

            for drone in picked:
                moves[drone] = fid
                deficits[fid] -= 1
                need -= 1
                if need <= 0:
                    break

            # Update deficit_fields for next iterations
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