"""
Greedy marginal-benefit adaptation strategy (enhanced):
- Objective: minimize expected field damage by prioritizing the most threatening fields and
  distributing remaining drones based on a simple marginal-benefit heuristic.
- Key ideas:
  1) Always focus on bringing the top-threat field to full protection first, using the closest drones.
  2) After top field is addressed, distribute any remaining drones to other threatened fields by
     maximizing a marginal-benefit score:
     marginal_benefit(field) ≈ threat_level * (1 - (current_protection + 1) / drones_for_full_protection)
     This captures diminishing returns as a field approaches full protection.
  3) Drones are assigned to exactly one group: "idle" or "protecting <Field_ID>".
  4) If a drone was previously en route or protecting a field and is not reassigned by the policy,
     we preserve its action by re-assigning it to the corresponding "protecting {target_id}" group.

- This approach aims to quickly calm the top threat while still providing beneficial protection to other fields
  whenever drones are available, without over-committing to a single field.

Note: It uses distance to field centers for tie-breaking and fast, deterministic decisions.
"""

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance_to_field_center(self, drone, field):
        cx, cy = self._field_center(field)
        loc = getattr(drone, "location", None)
        if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
            return float("inf")
        return math.hypot(loc.x - cx, loc.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify threatened fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort by threat level and pick the top field
        threat_fields.sort(key=lambda fld: fld.threat_level, reverse=True)
        top_field = threat_fields[0]

        # 3) Drones currently allocated to top field
        allocated_to_top = set()
        for d in components:
            if d.state in ("protecting", "moving_to_field") and d.target_id == top_field.id:
                allocated_to_top.add(d)

        # 4) Drones needed to reach full protection for top field
        current_top = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # 5) Fill top field with closest drones
        to_target = {}  # drone -> field_id
        for d in allocated_to_top:
            to_target[d] = top_field.id

        if needed_top > 0:
            candidates = []
            for d in components:
                if d in allocated_to_top:
                    continue
                dist = self._distance_to_field_center(d, top_field)
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            for _, d in candidates:
                if sum(1 for rd, fid in to_target.items() if fid == top_field.id) >= top_field.drones_for_full_protection:
                    break
                to_target[d] = top_field.id

        # 6) Compute current counts per field (including top field allocations)
        field_counts = {}
        for f in threat_fields:
            field_counts[f.id] = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
        for d, fid in to_target.items():
            if fid == top_field.id:
                field_counts[top_field.id] = field_counts[top_field.id] + 1

        # Capacities per field
        capacity = {f.id: f.drones_for_full_protection for f in threat_fields}

        # 7) Remaining drones for greedy distribution
        allocated_ids = set(to_target.keys())
        available = [d for d in components if d not in allocated_ids]

        centers = {f.id: self._field_center(f) for f in threat_fields}

        while available:
            best_drone = None
            best_field_id = None
            best_score = -1.0
            best_dist = float("inf")

            for d in available:
                dist_to_field = float("inf")
                candidate_field_id = None
                # Evaluate marginal benefit across all fields that still need protection
                for f in threat_fields:
                    if field_counts[f.id] >= capacity[f.id]:
                        continue
                    # Marginal benefit estimate
                    remaining_cap = max(1, capacity[f.id])
                    score = f.threat_level * (1.0 - (field_counts[f.id] + 1) / remaining_cap)
                    fx, fy = centers[f.id]
                    loc = getattr(d, "location", None)
                    if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                        dist = math.hypot(loc.x - fx, loc.y - fy)
                    else:
                        dist = float("inf")

                    if score > best_score or (abs(score - best_score) < 1e-9 and dist < best_dist):
                        best_score = score
                        best_drone = d
                        best_field_id = f.id
                        best_dist = dist

            if best_drone is None or best_score <= 0:
                break  # no beneficial assignments left

            to_target[best_drone] = best_field_id
            field_counts[best_field_id] += 1
            available.remove(best_drone)

        # 8) Final assignment, preserving existing actions where appropriate
        for d in components:
            if d in to_target:
                environment.assign_group(d, f"protecting {to_target[d]}")
            else:
                # Preserve current action if drone is already en route or protecting something
                if d.state in ("protecting", "moving_to_field") and d.target_id is not None:
                    environment.assign_group(d, f"protecting {d.target_id}")
                else:
                    environment.assign_group(d, "idle")