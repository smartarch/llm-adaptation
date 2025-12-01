from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields
        threatened = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]

        # 2) If no threatened fields, idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 3) Sort fields by threat (desc) and id (asc) for determinism
        threatened.sort(
            key=lambda f: (
                -float(getattr(f, "threat_level", 0.0)),
                str(getattr(f, "id", ""))
            )
        )

        # 4) Map current protectors by field
        current_by_field = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                if fid is not None:
                    current_by_field.setdefault(fid, []).append(d)

        # 5) Re-assign currently protecting drones to their groups
        assigned = set()
        for fid, ds in current_by_field.items():
            for dd in ds:
                environment.assign_group(dd, f"protecting {fid}")
                assigned.add(dd)

        # 6) Compute centers and needed drones per field
        centers = {}
        counts = {}      # current protecting count per field
        needs_full = {}  # drones still needed to reach full protection

        for f in threatened:
            fid = getattr(f, "id", None)
            cx = (getattr(f, "left", 0.0) + getattr(f, "right", 0.0)) / 2.0
            cy = (getattr(f, "top", 0.0) + getattr(f, "bottom", 0.0)) / 2.0
            centers[fid] = (cx, cy)

            req = int(getattr(f, "drones_for_full_protection", 0))
            if req < 0:
                req = 0
            current = len(current_by_field.get(fid, []))
            counts[fid] = current
            needs_full[fid] = max(0, req - current)

        # 7) If nothing needs protection, idle all non-assigned drones
        total_need = sum(needs_full.values())
        if total_need == 0:
            for d in components:
                if d not in assigned:
                    environment.assign_group(d, "idle")
            return

        # Available drones to assign (not already assigned)
        available = [d for d in components if d not in assigned]

        # Helper to get field center by fid
        def center_of(fid):
            return centers.get(fid, (0.0, 0.0))

        # 8) First pass: fill fields to full protection in threat order
        for f in threatened:
            fid = getattr(f, "id", None)
            need = needs_full.get(fid, 0)
            if need <= 0:
                continue
            cx, cy = center_of(fid)

            # Assign closest drones to this field until need is 0 or no drones left
            if not available:
                break
            # sort available by distance to this field center
            available.sort(key=lambda d: (
                (getattr(d, "location", None).x - cx) ** 2 +
                (getattr(d, "location", None).y - cy) ** 2
            ))
            while need > 0 and available:
                d = available.pop(0)
                environment.assign_group(d, f"protecting {fid}")
                assigned.add(d)
                need -= 1
                counts[fid] += 1
                needs_full[fid] = need

        # 9) If drones remain, allocate incrementally to highest-threat fields that still need protection
        while available:
            # Find the field with highest threat that still needs protection
            best_fid = None
            best_threat = -1.0
            best_need = 0
            for f in threatened:
                fid = getattr(f, "id", None)
                need = needs_full.get(fid, 0)
                if need > 0:
                    th = float(getattr(f, "threat_level", 0.0))
                    if th > best_threat or (th == best_threat and (best_fid is None or str(fid) < str(best_fid))):
                        best_threat = th
                        best_fid = fid
                        best_need = need

            if best_fid is None:
                break  # no field needs protection

            cx, cy = center_of(best_fid)
            # Pick the closest available drone to this field
            best_drone = None
            best_dist = None
            for d in available:
                loc = getattr(d, "location", None)
                dx = (loc.x if loc is not None else 0.0) - cx
                dy = (loc.y if loc is not None else 0.0) - cy
                dist2 = dx*dx + dy*dy
                if best_drone is None or dist2 < best_dist:
                    best_drone = d
                    best_dist = dist2

            if best_drone is None:
                break

            environment.assign_group(best_drone, f"protecting {best_fid}")
            assigned.add(best_drone)
            available.remove(best_drone)
            # Update need and counts
            needs_full[best_fid] -= 1
            counts[best_fid] += 1

        # 10) Any drones not assigned stay idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")