Reasoning and adaptation strategy

Goal
- Further reduce average damage by smarter, consistent, single-pass drone assignment.
- Use a more globally informed selection of which fields to fully protect, considering both threat levels and accessibility (distance) of idle drones.
- Ensure every drone is assigned exactly once in this pass, preserving existing protective actions when appropriate, and only reassigning idle drones.

Key ideas
- Phase 1: Use a distance-informed knapsack to decide which subset of threatening fields to fully protect given the currently idle drones. Each field has:
  - weight: drones needed to reach full protection (weight = drones_for_full_protection - current protectors on that field)
  - value: adjusted threat = threat_level divided by 1 plus a distance_cost
  - distance_cost: sum of distances from the weight closest idle drones to the field center (estimated travel effort)
- Phase 2: With remaining idle drones, allocate them to partially protect other threatening fields, prioritizing higher threat and proximity, while not disturbing fully protected fields.
- Phase 3: Build a single final plan mapping every drone to exactly one group. Drones already protecting a field but not touched in Phases 1/2 keep their current protecting group. All others become idle.
- This approach balances maximizing protection for accessible high-threat fields and still improving protection on other hotspots.

Python implementation

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatening fields
        fields = getattr(environment, "fields", [])
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, mark all drones idle
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Prepare helpers
        field_by_id = {getattr(f, "id"): f for f in threatening_fields if getattr(f, "id", None) is not None}

        # Current protectors per field (before planning)
        current_by_field = {}
        for fid in field_by_id.keys():
            current_by_field[fid] = len([
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid
            ])

        # Idle drones available for Phase 1
        idle_candidates = [d for d in components if getattr(d, "state", "") != "protecting"]
        idle_count = len(idle_candidates)

        # Build field infos for Phase 1
        field_infos = []
        for fid, field in field_by_id.items():
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = current_by_field.get(fid, 0)
            weight = max(0, required - current)
            if weight <= 0:
                continue

            # Compute distance_cost: sum of distances of the weight closest idle drones to this field
            # Field center
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            def dist2_to_field(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return dx*dx + dy*dy

            # Sort by distance to field center
            sorted_idle = sorted(idle_candidates, key=lambda d: dist2_to_field(d))

            if len(sorted_idle) < weight:
                # If not enough idle drones to fully protect, still compute a best-effort cost
                distance_cost = float("inf")
            else:
                distance_cost = sum(dist2_to_field(d) for d in sorted_idle[:weight])

            threat = float(getattr(field, "threat_level", 0.0))
            adj_value = threat / (1.0 + (distance_cost if distance_cost != float("inf") else 1e9))

            field_infos.append({
                "fid": fid,
                "field": field,
                "weight": int(weight),
                "threat": threat,
                "distance_cost": distance_cost,
                "adj_value": adj_value,
            })

        # Phase 1: knapsack to maximize adjusted threat given idle_count capacity
        chosen_full = set()
        if idle_count > 0 and field_infos:
            cap = idle_count
            dp_val = [-1.0] * (cap + 1)
            dp_choice = [None] * (cap + 1)
            dp_val[0] = 0.0
            dp_choice[0] = []

            for info in field_infos:
                w = info["weight"]
                v = info["adj_value"]
                fid = info["fid"]
                if w <= 0 or fid is None:
                    continue
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
        idle_remaining = list(idle_candidates)

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

        for fid in list(chosen_full):
            field = field_by_id.get(fid)
            if field is None:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = current_by_field.get(fid, 0)
            need = max(0, required - current)
            if need <= 0:
                continue
            cx, cy = center_of(field)
            # Choose closest idle drones not already planned
            candidates = [d for d in idle_remaining if d.id not in assigned_ids]
            if not candidates:
                continue
            candidates.sort(key=lambda d: dist2(d, cx, cy))

            for d in candidates[:need]:
                environment.assign_group(d, f"protecting {fid}")
                assigned_ids.add(d.id)
                idle_remaining.remove(d)

        # Phase 2: distribute remaining idle drones to partially protect other threatening fields
        remaining_idle = [d for d in idle_remaining]

        # Current protectors per field after Phase 1
        def current_protectors_after_phase1(fid):
            count = 0
            for d in components:
                if d.id in assigned_ids:
                    # Those assigned in Phase 1 to protecting fid
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                        count += 1
                else:
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                        count += 1
            return count

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
                environment.assign_group(d, f"protecting {fid}")
                assigned_ids.add(d.id)
            # refresh remaining list
            remaining_idle = [d for d in remaining_idle if d.id not in assigned_ids]

        # Phase 3: final plan (single assignment per drone)
        final_plan = {}

        for d in components:
            pid = d.id
            if pid in assigned_ids:
                # Assigned in Phases 1/2
                if pid in {k for k, v in []}:  # placeholder to keep structure explicit
                    pass
                # The plan for these drones is already set via environment in Phases 1/2.
                # We'll reconstruct a record for completeness.
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) is not None:
                    final_plan[pid] = f"protecting {getattr(d, 'target_id', None)}"
                else:
                    # If somehow not equal, default to current or idle
                    if pid in assigned_ids:
                        final_plan[pid] = "idle"
                    else:
                        final_plan[pid] = "idle"
            else:
                # Not explicitly assigned in Phases 1/2: preserve current protecting group if any, else idle
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) is not None:
                    final_plan[pid] = f"protecting {getattr(d, 'target_id', None)}"
                else:
                    final_plan[pid] = "idle"

        # Apply final plan with exactly one assignment per drone
        for d in components:
            grp = final_plan.get(d.id, "idle")
            environment.assign_group(d, grp)
```