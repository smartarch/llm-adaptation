from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", [])
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, mark all drones idle
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Map field_id -> field and compute current protectors per field
        field_by_id = {getattr(f, "id"): f for f in threatening_fields}
        current_protectors_by_field = {}
        for f in threatening_fields:
            fid = getattr(f, "id", None)
            if fid is None:
                continue
            current_protectors_by_field[fid] = [
                d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid
            ]

        # Build field info for Phase 1 knapsack
        field_infos = []
        idle_drones = [d for d in components if getattr(d, "state", "") != "protecting"]
        idle_count = len(idle_drones)

        for f in threatening_fields:
            fid = getattr(f, "id", None)
            if fid is None:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            current = len(current_protectors_by_field.get(fid, []))
            weight = max(0, required - current)
            if weight <= 0:
                # Already fully protected; nothing to allocate
                continue
            field_infos.append({
                "field": f,
                "id": fid,
                "weight": int(weight),
                "required": required,
                "current": current,
                "threat": float(getattr(f, "threat_level", 0.0)),
            })

        # Phase 1: knapsack to maximize threat protection given idle_count capacity
        chosen_ids_for_full = set()
        if idle_count > 0 and field_infos:
            cap = idle_count
            # dp_val[c] = best threat value, dp_choice[c] = list of field ids chosen to reach that value
            dp_val = [-1.0] * (cap + 1)
            dp_choice = [None] * (cap + 1)
            dp_val[0] = 0.0
            dp_choice[0] = []

            for info in field_infos:
                w = info["weight"]
                v = info["threat"]
                fid = info["id"]
                if w <= 0 or fid is None:
                    continue
                for c in range(cap, w - 1, -1):
                    if dp_val[c - w] >= 0:
                        nv = dp_val[c - w] + v
                        if nv > dp_val[c]:
                            dp_val[c] = nv
                            dp_choice[c] = (dp_choice[c - w] or []) + [fid]

            # pick best capacity
            best_c = max(range(cap + 1), key=lambda c: dp_val[c] if dp_val[c] >= 0 else -1)
            if dp_val[best_c] >= 0:
                chosen_ids_for_full = set(dp_choice[best_c] or [])

        # Phase 1 allocation: assign closest idle drones to chosen fields
        assigned_ids = set()
        # Helper to center of a field
        def field_center(field):
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        # Helper to distance squared
        def dist2_location(loc, cx, cy):
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return dx*dx + dy*dy

        for fid in chosen_ids_for_full:
            field = field_by_id.get(fid)
            if field is None:
                continue
            # how many more drones needed to reach full protection
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = len([d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid])
            need = max(0, required - current)
            if need <= 0:
                continue

            cx, cy = field_center(field)
            # candidates: idle drones not already assigned
            candidates = [d for d in idle_drones if d.id not in assigned_ids]
            candidates.sort(key=lambda d: dist2_location(getattr(d, "location", None), cx, cy))

            for d in candidates[:need]:
                environment.assign_group(d, f"protecting {fid}")
                assigned_ids.add(d.id)

        # Phase 2: distribute remaining idle drones to partially protect other threatening fields
        remaining_idle = [d for d in idle_drones if d.id not in assigned_ids]

        # Recompute current protectors per field after Phase 1
        current_by_field = {}
        for f in threatening_fields:
            fid = getattr(f, "id", None)
            if fid is None:
                continue
            current_by_field[fid] = len([d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid])

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(threatening_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for field in fields_sorted:
            fid = getattr(field, "id", None)
            if fid is None:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = current_by_field.get(fid, 0)
            need = max(0, required - current)
            if need <= 0:
                continue
            if not remaining_idle:
                break

            cx, cy = field_center(field)
            remaining_idle.sort(key=lambda d: dist2_location(getattr(d, "location", None), cx, cy))

            for d in remaining_idle[:need]:
                environment.assign_group(d, f"protecting {fid}")
                assigned_ids.add(d.id)
            remaining_idle = [d for d in remaining_idle if d.id not in assigned_ids]

        # Final pass: ensure all drones are assigned to a group
        for d in components:
            if d.id in assigned_ids:
                # Ensure the protecting group matches the current target
                if getattr(d, "state", "") == "protecting":
                    environment.assign_group(d, f"protecting {getattr(d, 'target_id', None)}")
                else:
                    t = getattr(d, "target_id", None)
                    environment.assign_group(d, f"protecting {t}")
            else:
                # If not assigned, make idle
                if getattr(d, "state", "") != "protecting":
                    environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, f"protecting {getattr(d, 'target_id', None)}")