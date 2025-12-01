Reasoning and adaptation strategy

Goal
- Fix the test failures by ensuring every drone is assigned exactly once in a single pass.
- Compute a single final plan that maps every drone to a group, then apply it with one environment.assign_group call per drone.
- Preserve existing protections when drones are already protecting a field and not involved in the current planning.
- Allocate idle drones first to fully protect as many high-threat fields as possible (subject to feasibility), prioritizing proximity to fields. Then, with any remaining idle drones, partially protect other threatening fields, again preferring proximity. Finally, assign all drones to their determined final groups.

Key approach
- Phase 1: Build a knapsack to decide which subset of threatening fields to fully protect given the number of idle drones. Weight = drones needed to reach full protection for that field; value = field threat level. Only idle drones are considered as resource.
- Phase 2: For the chosen subset, assign the closest idle drones to each field to achieve full protection. Drones are allocated exclusively (no drone is assigned to multiple fields).
- Phase 3: With any remaining idle drones, greedily distribute them to partially protect other threatening fields, prioritizing higher threat and proximity, without disturbing fields already fully protected.
- Phase 4: Build a final plan for all drones:
  - Drones allocated in Phase 1/2 have their assigned protecting group.
  - Drones already protecting a field but not touched in Phases 1/2 keep their current protecting group.
  - All others become idle.
- Finally, apply the plan with exactly one environment.assign_group call per drone.

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

        # If no threats, all drones idle (single plan)
        if not threatening_fields:
            final_plan = {d.id: "idle" for d in components}
            for d in components:
                environment.assign_group(d, final_plan[d.id])
            return

        # Map field_id -> field for quick access
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
            field_infos.append({
                "fid": fid,
                "field": field,
                "weight": weight,
                "threat": float(getattr(field, "threat_level", 0.0)),
            })

        # Phase 1: knapsack to maximize threat given idle_count capacity
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
        plan = {}  # per-drone final plan (used to build final_plan)
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
            # Candidates: idle drones not already planned
            candidates = [d for d in idle_remaining if d.id not in plan]
            if not candidates:
                continue
            candidates.sort(key=lambda d: dist2(d, cx, cy))

            for d in candidates[:need]:
                plan[d.id] = f"protecting {fid}"
                assigned_ids.add(d.id)
                idle_remaining.remove(d)

        # Phase 2: distribute remaining idle drones to partially protect other threatening fields
        remaining_idle = [d for d in idle_remaining]

        # Current protectors per field after Phase 1 (count those in plan plus existing protectors)
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
                assigned_ids.add(d.id)
            # refresh remaining list
            remaining_idle = [d for d in remaining_idle if d.id not in assigned_ids]

        # Phase 3: finalize a single final plan (mapping every drone)
        final_plan = {}

        # Drones explicitly planned in Phase 1/2
        for d in components:
            if d.id in plan:
                final_plan[d.id] = plan[d.id]

        # Drones not explicitly planned: preserve current protecting group if any, else idle
        for d in components:
            if d.id in final_plan:
                continue
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) is not None:
                final_plan[d.id] = f"protecting {getattr(d, 'target_id', None)}"
            else:
                final_plan[d.id] = "idle"

        # Apply the final plan with exactly one assignment per drone
        for d in components:
            grp = final_plan.get(d.id, "idle")
            environment.assign_group(d, grp)
```