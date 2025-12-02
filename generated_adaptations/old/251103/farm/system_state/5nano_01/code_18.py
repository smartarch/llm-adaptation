"""
Reasoning and adaptation strategy (enhanced):
- Objective: minimize field damage by robustly distributing drones.
- Core idea:
  1) Always target the top-threat field (highest threat_level) first and push it toward full protection using the closest drones.
  2) After top field handling, distribute any remaining drones greedily to other threatened fields.
     For each remaining drone, compute a per-drone, per-field marginal score that considers:
       - field threat level (higher is better)
       - remaining protection need relative to field capacity (to capture diminishing returns)
       - travel time (distance to field center; closer is preferred)
     We greedily select the (drone, field) pair with the highest score, updating needs as drones are allocated.
  3) Every drone is assigned to exactly one group: "idle" or "protecting <Field_ID>".
  4) If a drone was already en route or protecting and is not reassigned by the policy, we preserve its action by re-assigning it to the corresponding "protecting {target_id}" group.

- This approach aims for rapid stabilization of the most dangerous field while still providing meaningful protection to others when drones are available, and it explicitly accounts for travel time in tie-breaking.

Code implements:
- Closest-drone-first filling of the top field to full capacity.
- A greedy, marginal-benefit distribution for remaining drones across other threatened fields.
- Final mapping of drones to groups with sensible preservation of ongoing actions.

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

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort threat fields by threat level and pick the top field
        threat_fields.sort(key=lambda fld: fld.threat_level, reverse=True)
        top_field = threat_fields[0]

        # 3) Drones currently allocated to top field
        allocated_to_top = set()
        for d in components:
            if d.state in ("protecting", "moving_to_field") and d.target_id == top_field.id:
                allocated_to_top.add(d)

        # 4) Drones needed for top field to reach full protection
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

            current_top_count = sum(1 for dd, fid in to_target.items() if fid == top_field.id)
            for _, d in candidates:
                if current_top_count >= top_field.drones_for_full_protection:
                    break
                to_target[d] = top_field.id
                current_top_count += 1

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

        # Greedy distribution: select the best (drone, field) pair iteratively
        while available:
            best_pair = None  # (drone, field_id)
            best_score = -1.0
            best_dist = float("inf")

            for d in available:
                best_for_d_field = None
                best_for_d_score = -1.0
                best_for_d_dist = float("inf")

                for f in threat_fields:
                    if field_counts[f.id] >= capacity[f.id]:
                        continue
                    need = capacity[f.id] - field_counts[f.id]
                    # Marginal score: higher threat and larger remaining need => higher score
                    base = f.threat_level * (need / max(1, capacity[f.id]))
                    fx, fy = centers[f.id]
                    dist = self._distance_to(d, f)
                    score = base / (dist + 1e-6)  # penalize travel time

                    if score > best_for_d_score or (abs(score - best_for_d_score) < 1e-12 and dist < best_for_d_dist):
                        best_for_d_score = score
                        best_for_d_field = f.id
                        best_for_d_dist = dist

                if best_for_d_field is not None:
                    if best_for_d_score > best_score or (abs(best_for_d_score - best_score) < 1e-12 and best_for_d_dist < best_dist):
                        best_pair = (d, best_for_d_field)
                        best_score = best_for_d_score
                        best_dist = best_for_d_dist

            if best_pair is None or best_score <= 0:
                break  # no beneficial assignments left

            d, fid = best_pair
            to_target[d] = fid
            field_counts[fid] += 1
            available.remove(d)

        # 8) Final assignment: map drones to groups
        for d in components:
            if d in to_target:
                environment.assign_group(d, f"protecting {to_target[d]}")
            else:
                # Preserve existing action if drone is already en route or protecting
                if d.state in ("protecting", "moving_to_field") and d.target_id is not None:
                    environment.assign_group(d, f"protecting {d.target_id}")
                else:
                    environment.assign_group(d, "idle")