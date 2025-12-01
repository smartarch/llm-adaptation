from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Precompute field centers
        centers = {}
        for f in fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Current defenders per field
        current_defenders = {f.id: 0 for f in fields}
        current_defenders_set = {f.id: set() for f in fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_defenders:
                    current_defenders[tid] += 1
                    current_defenders_set[tid].add(c)

        D = len(components)

        # Build list of fields with their "cost" to reach full protection and a benefit ratio
        # cost = additional drones needed beyond current defenders
        field_infos = []
        for f in fields:
            current = current_defenders.get(f.id, 0)
            cost = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            threat = getattr(f, "threat_level", 0.0)
            if cost <= 0:
                ratio = float('inf')  # already fully protected
            else:
                ratio = threat / max(1, cost)
            field_infos.append((ratio, f.id, cost, current))

        # Sort by ratio desc, then threat desc as a tiebreaker
        field_infos.sort(key=lambda x: (x[0], getattr(next((f for f in fields if f.id == x[1]), None), "threat_level", 0)), reverse=True)

        # Phase 1: select which fields to attempt to fully protect
        selected_fields = []
        allocated_cost = 0
        # Rebuild a quick map for quick access in the loop
        current_map = {f.id: current_defenders.get(f.id, 0) for f in fields}
        for ratio, fid, cost, cur in field_infos:
            if cost == 0:
                # Already fully protected; automatically include
                selected_fields.append(fid)
                continue
            if allocated_cost + cost <= D:
                selected_fields.append(fid)
                allocated_cost += cost
            else:
                break

        # Phase 2: allocate drones to meet full protection for selected fields
        final_group = {}  # drone -> group_id
        allocated_drones = set()

        # Helper to record existing defenders for a field into final_group
        def ensure_existing_defenders(field_id):
            for c in current_defenders_set.get(field_id, set()):
                if c not in allocated_drones and c not in final_group:
                    final_group[c] = f"protecting {field_id}"
                    allocated_drones.add(c)

        # First, ensure existing defenders for selected fields are represented
        for fid in selected_fields:
            ensure_existing_defenders(fid)

        # Now allocate needed drones to each selected field (closest first)
        for fid in selected_fields:
            required = getattr(next((f for f in fields if f.id == fid), None), "drones_for_full_protection", 0)
            current = current_defenders.get(fid, 0)
            need = max(0, required - current)
            if need <= 0:
                continue

            cx, cy = centers[fid]

            # Build candidate drones: those not already allocated to any final group
            candidates = []
            for c in components:
                if c in allocated_drones:
                    continue
                # Do not consider drones already protecting this field
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                    continue
                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                candidates.append((dist2, c))

            candidates.sort(key=lambda t: t[0])

            allocated_here = 0
            for dist2, drone in candidates:
                if allocated_here >= need:
                    break
                final_group[drone] = f"protecting {fid}"
                allocated_drones.add(drone)
                allocated_here += 1

            # If there are already defenders, ensure they are represented
            if current_defenders.get(fid, 0) > 0:
                ensure_existing_defenders(fid)

        # Phase 3: partial protection with remaining drones (one per top-field not fully protected)
        # Build list of fields not yet fully protected, ordered by threat
        not_full = []
        for f in fields:
            required = getattr(f, "drones_for_full_protection", 0)
            current = current_defenders.get(f.id, 0)
            if required > current:
                not_full.append((f.threat_level, f))

        not_full.sort(key=lambda t: t[0], reverse=True)
        unassigned = [c for c in components if c not in allocated_drones and c not in final_group]

        for _, f in not_full:
            if not unassigned:
                break
            cx, cy = centers[f.id]
            best_idx = None
            best_dist = float('inf')
            for idx, drone in enumerate(unassigned):
                loc = getattr(drone, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                if dist2 < best_dist:
                    best_dist = dist2
                    best_idx = idx
            if best_idx is not None:
                drone = unassigned.pop(best_idx)
                final_group[drone] = f"protecting {f.id}"
                allocated_drones.add(drone)

        # Phase 4: assign remaining drones to idle
        for c in components:
            if c in final_group:
                environment.assign_group(c, final_group[c])
            else:
                environment.assign_group(c, "idle")