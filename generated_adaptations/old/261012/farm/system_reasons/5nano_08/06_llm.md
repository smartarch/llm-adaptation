Strategy reasoning and plan for improvement

Goal
- Further reduce damage by improving how drones are allocated to fully protected fields while respecting constraints:
  - Only fully protected fields (no partial protection) contribute to protection.
  - Avoid over-protecting a field beyond its drones_for_full_protection.
  - Prefer protecting the most threatening fields first, but also consider how many drones are available.
  - Maintain continuity to reduce churn (drones stay with the same field when possible).
  - Ensure exactly one assignment per drone per step (no intermediate reassignments).

Key enhancements
- Global, single-pass planning: Build a final plan for all drones, then apply in one pass to satisfy the “one assignment per drone” rule.
- Subset selection for full protection: Use a lightweight greedy knapsack-like approach to decide which fields to fully protect given the current number of drones. Score fields by threat level per required drones (threat_level / max(1, drones_for_full_protection)) and select fields in that order as long as their total capacity fits in N drones.
- Continuity-aware allocation: When selecting drones for a protected field, prefer drones that were protecting the same field previously (to satisfy the continuity constraint) and otherwise use proximity to the field center as a secondary criterion.
- Safe fallback: Drones not selected for protection are assigned to idle in the final plan.

What changes were made
- Implemented a fresh, cleaner allocation that:
  - Chooses a subset of fields to fully protect based on threat and capacity (greedy with a meaningful score).
  - Assigns drones to each chosen field in a single pass, respecting capacity and continuity.
  - Assigns all remaining drones to idle.
  - Applies all assignments in one pass to ensure each drone is assigned exactly once.

Python code

```py
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of previous assignments: map drone_id -> group_id
        self._prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Allocation strategy:
        - Identify fields with threat_level > 0.
        - Select a subset of fields to fully protect using a greedy score: threat_level / max(1, capacity).
        - Allocate drones to selected fields, prioritizing continuity (drones that protected the same field previously)
          and then proximity to the field center.
        - All other drones are assigned to idle.
        - Apply all assignments in a single pass to ensure each drone is assigned exactly once.
        """
        # Helper: field center
        def field_center_coords(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: distance from drone to a point
        def dist_to_point(drone, pt):
            dx = getattr(drone.location, "x", 0.0) - pt[0]
            dy = getattr(drone.location, "y", 0.0) - pt[1]
            return (dx * dx + dy * dy) ** 0.5

        # 1) Gather threat fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
                self._prev_assignments[id(c)] = "idle"
            return

        # Sort threat fields by threat level descending (and then by capacity if needed)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        N = len(components)

        # Compute a score for each field: threat_level / max(1, capacity)
        def field_score(field):
            cap = getattr(field, "drones_for_full_protection", 0)
            if cap <= 0:
                return -1.0
            thr = getattr(field, "threat_level", 0.0)
            return thr / max(1, cap)

        threat_fields = sorted(threat_fields, key=field_score, reverse=True)

        # 2) Select which fields to fully protect given total drone budget N
        selected_fields = []
        used_capacity = 0
        for f in threat_fields:
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            if used_capacity + cap <= N:
                selected_fields.append(f)
                used_capacity += cap

        # 3) Allocate drones to selected fields (single pass)
        plan = {}  # drone_id -> group_name
        available = list(components)

        # Distance helpers
        centers = {f.id: field_center_coords(f) for f in threat_fields}

        def center_of(field):
            return centers.get(field.id, (0.0, 0.0))

        def priority_key(drone, fid, center):
            # Prefer drones that previously protected this field
            prev = self._prev_assignments.get(id(drone))
            if prev == f"protecting {fid}":
                return (0, dist_to_point(drone, center))
            return (1, dist_to_point(drone, center))

        # For each selected field, assign up to its capacity
        for f in selected_fields:
            fid = f.id
            cap = getattr(f, "drones_for_full_protection", 0)
            center = center_of(f)

            if cap <= 0:
                continue
            # Sort available drones by continuity + distance
            available.sort(key=lambda d: priority_key(d, fid, center))
            chosen = available[:cap]

            for d in chosen:
                plan[id(d)] = f"protecting {fid}"
                self._prev_assignments[id(d)] = f"protecting {fid}"
            # Remove chosen from available
            available = available[cap:]

        # 4) Any remaining drones go idle
        for d in available:
            plan[id(d)] = "idle"
            self._prev_assignments[id(d)] = "idle"

        # 5) Apply all assignments in a single pass
        for c in components:
            gid = plan.get(id(c), "idle")
            environment.assign_group(c, gid)

```