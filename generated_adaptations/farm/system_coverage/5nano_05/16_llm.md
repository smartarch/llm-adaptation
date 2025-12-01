Reasoning and adaptation strategy

Goal
- Improve robustness and performance while keeping a single-pass, explicit assignment per drone.
- Use a simple, predictable heuristic that tends to maximize protection for the most threatening fields that are feasible to cover with the currently idle drones, prioritizing closer drones to reduce travel time.
- Preserve existing protections when drones are already protecting a field and not involved in the current planning.
- Ensure every drone is assigned exactly once in this pass.

Key ideas
- Phase 1 (core): Fully protect as many threatening fields as possible given the number of idle drones. We choose fields by a density metric (threat level relative to how many drones are still needed to full protection). For ties or close cases, we prefer fields with higher threat and lower required weight.
- Allocation within Phase 1: For each selected field, assign the closest available idle drones to reach the field’s required protection.
- Phase 2 (optional, lightweight): With any remaining idle drones, greedily provide partial protection to other threatening fields by giving 1 drone at a time to the highest-threat field that still needs protection, always taking the closest drone available.
- Phase 3: Build a single final plan mapping every drone to one group. Drones that were already protecting a field and were not reassigned stay in their current protecting group. All others become idle. Apply the final plan with exactly one environment.assign_group call per drone.

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

        # If no threats, assign all drones to idle (single-pass plan)
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
            weight = max(0, required - current)  # drones still needed to fully protect
            if weight <= 0:
                continue
            # Density heuristic: higher threat with lower weight is more attractive
            threat = float(getattr(field, "threat_level", 0.0))
            density = threat / max(1, weight)
            field_infos.append({
                "fid": fid,
                "field": field,
                "weight": weight,
                "threat": threat,
                "density": density,
            })

        # Phase 1: greedy selection by density (threat_per_weight)
        chosen_full = set()
        if idle_count > 0 and field_infos:
            # Sort by density (desc), tie-breaker by threat (desc), then by weight (asc)
            field_infos.sort(key=lambda x: (x["density"], x["threat"], -x["weight"]), reverse=True)
            available = list(idle_candidates)
            for info in field_infos:
                fid = info["fid"]
                weight = int(info["weight"])
                if weight <= 0:
                    continue
                # Current protectors for this field
                current = current_by_field.get(fid, 0)
                need = max(0, int(info["weight"]) - current)
                if need <= 0:
                    continue
                if not available:
                    break
                # Center of the field
                field = info["field"]
                left = getattr(field, "left", 0.0)
                right = getattr(field, "right", 0.0)
                top = getattr(field, "top", 0.0)
                bottom = getattr(field, "bottom", 0.0)
                cx = (left + right) / 2.0
                cy = (top + bottom) / 2.0

                # Pick the closest available drones
                def dist2(d, cx=cx, cy=cy):
                    loc = getattr(d, "location", None)
                    if loc is None:
                        return float("inf")
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    return dx*dx + dy*dy

                available.sort(key=lambda d: dist2(d, cx, cy))
                picks = available[:min(need, len(available))]
                for d in picks:
                    # Schedule to this field
                    if d.id not in planned_ids:
                        pass  # placeholder to show intent; actual plan stored below
                # We'll build the final plan in a separate dict in Phase 2/Final, to ensure single per-drone assignment
                # To keep it simple and robust, we directly assign in a local plan map below.
                for d in picks:
                    d_plan_id = d.id
                    planned_ids.add(d_plan_id)
                    # store in plan dict (per-drone)
                    plan[d_plan_id] = f"protecting {fid}"
                # Remove picks from available
                available = [d for d in available if d.id not in {p.id for p in picks}]
                if len(picks) > 0:
                    chosen_full.add(fid)

        # Phase 2: with remaining idle drones, provide minimal partial protection
        remaining_idle = [d for d in idle_candidates if d.id not in plan]

        # Current protectors per field after Phase 1 (count those in plan + existing protectors)
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
            # Center for this field
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0

            remaining_idle.sort(key=lambda d: (
                (getattr(d, "location", None).x - cx) ** 2 +
                (getattr(d, "location", None).y - cy) ** 2
                if getattr(d, "location", None) is not None else float("inf")
            ))
            for d in remaining_idle[:need]:
                plan[d.id] = f"protecting {fid}"
            remaining_idle = [d for d in remaining_idle if d.id not in plan]

        # Phase 3: Finalize a single final plan mapping every drone
        final_plan = {}

        # Apply explicit plan for drones we decided in Phases 1/2
        for d in components:
            pid = d.id
            if pid in plan:
                final_plan[pid] = plan[pid]

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