from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatening fields
        fields = getattr(environment, "fields", [])
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        plan = {}

        if threatening_fields:
            # Prepare helpers
            field_by_id = {getattr(f, "id"): f for f in threatening_fields if getattr(f, "id", None) is not None}

            # Current protectors per field (before planning)
            current_by_field = {}
            for fid, f in field_by_id.items():
                current_by_field[fid] = len([
                    d for d in components
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid
                ])

            # Idle drones available for Phase 1
            idle_candidates = [d for d in components if getattr(d, "state", "") != "protecting"]
            idle_count = len(idle_candidates)

            # Build field infos for Phase 1 (to fill to full protection)
            field_infos = []
            weight_by_field = {}
            for fid, f in field_by_id.items():
                required = int(getattr(f, "drones_for_full_protection", 0))
                current = current_by_field.get(fid, 0)
                weight = max(0, required - current)  # drones still needed to fully protect
                if weight > 0:
                    field_infos.append({
                        "fid": fid,
                        "field": f,
                        "weight": weight,
                        "threat": float(getattr(f, "threat_level", 0.0)),
                    })
                    weight_by_field[fid] = weight

            # Phase 1: knapsack to maximize threat reduction given idle_count capacity
            chosen_full = set()
            if idle_count > 0 and field_infos:
                cap = idle_count
                dp_val = [-1.0] * (cap + 1)
                dp_choice = [None] * (cap + 1)
                dp_val[0] = 0.0
                dp_choice[0] = []
                for info in field_infos:
                    w = info["weight"]
                    v = info["threat"]
                    fid = info["fid"]
                    for c in range(cap, w - 1, -1):
                        if dp_val[c - w] >= 0:
                            nv = dp_val[c - w] + v
                            if nv > dp_val[c]:
                                dp_val[c] = nv
                                dp_choice[c] = (dp_choice[c - w] or []) + [fid]
                best_c = max(range(cap + 1), key=lambda c: dp_val[c] if dp_val[c] >= 0 else -1)
                if dp_val[best_c] >= 0:
                    chosen_full = set(dp_choice[best_c] or [])

            # Phase 1: assign closest idle drones to chosen fields
            assigned_ids = set()
            assigned_per_field = {fid: 0 for fid in chosen_full}

            def center_of(field):
                left = getattr(field, "left", 0.0)
                right = getattr(field, "right", 0.0)
                top = getattr(field, "top", 0.0)
                bottom = getattr(field, "bottom", 0.0)
                return ((left + right) / 2.0, (top + bottom) / 2.0)

            def dist2(drone, cx, cy):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return dx*dx + dy*dy

            idle_remaining = list(idle_candidates)

            for fid in chosen_full:
                field = field_by_id.get(fid)
                if field is None:
                    continue
                required = int(getattr(field, "drones_for_full_protection", 0))
                current = current_by_field.get(fid, 0)
                need = max(0, required - current)
                if need <= 0:
                    continue
                cx, cy = center_of(field)
                # Recompute idle candidates excluding already planned
                candidates = [d for d in idle_remaining if d.id not in plan]
                if not candidates:
                    continue
                candidates.sort(key=lambda d: dist2(d, cx, cy))
                for d in candidates[:need]:
                    plan[d.id] = f"protecting {fid}"
                    idle_remaining.remove(d)
                    assigned_ids.add(d.id)
                    assigned_per_field[fid] = assigned_per_field.get(fid, 0) + 1

            # Phase 2: distribute remaining idle drones to partially protect other threatening fields
            remaining_idle = [d for d in components if d.id not in plan and getattr(d, "state", "") != "protecting"]

            # Helper: current protectors per field after Phase 1 (including Phase 1 assignments)
            def current_protectors_after_phase1(fid):
                count = 0
                for d in components:
                    if d.id in plan:
                        if plan[d.id] == f"protecting {fid}":
                            count += 1
                    else:
                        if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                            count += 1
                return count

            # Sort threatening fields by threat (high to low)
            threatening_fields_sorted = sorted(threatening_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

            for field in threatening_fields_sorted:
                fid = getattr(field, "id", None)
                if fid is None:
                    continue
                required = int(getattr(field, "drones_for_full_protection", 0))
                current = current_protectors_after_phase1(fid)
                need = max(0, required - current)
                if need <= 0:
                    continue
                if not remaining_idle:
                    break

                cx, cy = center_of(field)
                remaining_idle.sort(key=lambda d: dist2(d, cx, cy))
                for d in remaining_idle[:need]:
                    plan[d.id] = f"protecting {fid}"
                    remaining_idle.remove(d)

        # Phase 3: finalize plan for all drones
        # Ensure every drone has exactly one assignment
        final_plan = {}

        # First, apply our plan for drones we decided in Phases 1/2
        for d in components:
            pid = d.id
            if pid in plan:
                final_plan[pid] = plan[pid]
            else:
                # Drones not explicitly planned: preserve current protecting group if any, else idle
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) is not None:
                    final_plan[pid] = f"protecting {getattr(d, 'target_id', None)}"
                else:
                    final_plan[pid] = "idle"

        # Ensure all final groups are valid (defensive)
        for d in components:
            grp = final_plan.get(d.id, "idle")
            # If the plan somehow refers to an invalid field, fallback to idle
            if grp.startswith("protecting "):
                fid = grp.split("protecting ", 1)[1]
                # If field id is not known, fallback
                if fid not in [getattr(t, "id", None) for t in threatening_fields]:
                    final_plan[d.id] = "idle"

        # Apply final plan with exactly one assignment per drone
        for d in components:
            grp = final_plan.get(d.id, "idle")
            environment.assign_group(d, grp)