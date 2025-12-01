from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # 2) If no threatened fields, idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 3) Sort threatened fields by threat level (desc) then id (asc)
        threatened.sort(
            key=lambda f: (-getattr(f, "threat_level", 0), str(getattr(f, "id", "")))
        )

        # 4) Map current protectors by field
        current_by_field = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                if fid is not None:
                    current_by_field.setdefault(fid, []).append(d)

        # 5) Re-assign currently protecting drones to their groups (explicit)
        assigned = set()
        for fid, ds in current_by_field.items():
            for dd in ds:
                environment.assign_group(dd, f"protecting {fid}")
                assigned.add(dd)

        # 6) Compute centers and needed drones per field
        centers = {}
        needed = {}
        for f in threatened:
            fid = getattr(f, "id", None)
            centers[fid] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req < 0:
                req = 0
            current = len(current_by_field.get(fid, []))
            need = max(0, req - current)
            needed[fid] = need

        # 7) Greedy allocation: allocate closest available drones to fields with need > 0
        remaining = len(components) - len(assigned)
        if remaining > 0:
            # While there is any field needing protection and we have drones left
            while True:
                # Choose the field with highest threat among those with need > 0
                best_field = None
                best_threat = -1.0
                for f in threatened:
                    fid = getattr(f, "id", None)
                    if needed.get(fid, 0) > 0:
                        th = getattr(f, "threat_level", 0.0)
                        if th > best_threat or (th == best_threat and (best_field is None or str(fid) < str(getattr(best_field, "id", ""))):
                            best_field = f
                            best_threat = th
                if best_field is None:
                    break  # no field needs protection

                fid = getattr(best_field, "id", None)
                cx, cy = centers[fid]

                # Pick the closest unassigned drone
                best_drone = None
                best_dist = None
                for d in components:
                    if d in assigned:
                        continue
                    loc = getattr(d, "location", None)
                    dx = (loc.x if loc is not None else 0.0) - cx
                    dy = (loc.y if loc is not None else 0.0) - cy
                    dist2 = dx*dx + dy*dy
                    if best_drone is None or dist2 < best_dist:
                        best_drone = d
                        best_dist = dist2

                if best_drone is None:
                    break  # no drones left to allocate

                # Assign this drone to the field
                environment.assign_group(best_drone, f"protecting {fid}")
                assigned.add(best_drone)
                remaining -= 1
                needed[fid] -= 1

        # 8) Any drones not assigned go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")