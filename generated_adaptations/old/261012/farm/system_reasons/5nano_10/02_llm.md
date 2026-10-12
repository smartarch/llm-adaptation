Strategy and reasoning

Goal
- Split the fleet of drones into groups so that the most threatened field is fully protected, using the closest drones available.
- Do not over-protect fields (don’t exceed drones_for_full_protection for any field).
- Maintain a reasonable level of active protection (at least half the drones protecting fields most of the time).
- Avoid excessive churn (keep drones assigned to the same field for at least 25% of the time for roughly half the drones).
- If there are no threatened fields, default to idle.

Key ideas
- Identify the currently most threatened field (highest threat_level > 0).
- Force full protection for that field by assigning drones up to its drones_for_full_protection, prioritizing the closest drones to that field. Distances are computed to the field’s center.
- If there are spare drones, distribute them to the next-most-threatened fields up to their drones_for_full_protection, in threat-descending order.
- Ensure at least half of the drones are protecting some field by boosting protection for fields up to the min_protect threshold if needed (without exceeding per-field max).
- To respect the “stability” requirement, when selecting drones for each field, use a distance-based ordering with a tie-breaker that favors drones that were protecting that same field in the previous step. This helps keep drones on the same field when beneficial.
- Maintain a memory of previous assignments to drive the stability behavior. Explicitly re-assign each drone to its chosen group every step (even if it ends up the same as before, per the requirement).

Implementation details
- Groups:
  - "idle" for idle drones.
  - For each field with threat_level > 0: "protecting {field.id}"
- The adaptation uses an internal memory dict self._prev_assignments mapping drone -> group_id from the previous step to guide stability decisions.
- Distance to a field center is used to pick the closest drones. For top-field selection, we bias toward drones that were already protecting that field in the previous step to improve stability.

Code (Python)

```py
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation
from typing import List

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of previous assignments: drone -> group_id
        self._prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        n = len(drones)

        # If no drones, nothing to do
        if n == 0:
            return

        # Discover threatened fields (threat_level > 0), sorted by threat desc
        threatened_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Prepare field -> group mapping
        field_group_map = {}
        for f in threatened_fields:
            field_group_map[f.id] = f"protecting {f.id}"

        # Compute desired number of drones per field
        desired_by_field = {}
        min_protect = (n + 1) // 2  # at least half protecting

        if threatened_fields:
            top_field = threatened_fields[0]
            top_group = field_group_map[top_field.id]
            max_top = int(getattr(top_field, "drones_for_full_protection", 0))
            max_top = max(0, min(max_top, n))
            desired_by_field[top_field.id] = max_top
            remaining = n - max_top

            # Allocate to subsequent fields in threat order
            for f in threatened_fields[1:]:
                if remaining <= 0:
                    break
                max_for_field = int(getattr(f, "drones_for_full_protection", 0))
                take = min(max_for_field, remaining)
                if take > 0:
                    desired_by_field[f.id] = take
                    remaining -= take

            # If total desired < min_protect, boost protection up to limits to meet threshold
            total_desired = sum(desired_by_field.values()) if desired_by_field else 0
            if total_desired < min_protect:
                for f in threatened_fields:
                    if total_desired >= min_protect:
                        break
                    cur = desired_by_field.get(f.id, 0)
                    cap = int(getattr(f, "drones_for_full_protection", 0))
                    if cur < cap:
                        add = min(cap - cur, min_protect - total_desired)
                        if add > 0:
                            desired_by_field[f.id] = cur + add
                            total_desired += add

        # Compute centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        def dist_to_field(drone, field):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            x = getattr(loc, "x", 0.0)
            y = getattr(loc, "y", 0.0)
            cx, cy = field_centers.get(field.id, (0.0, 0.0))
            dx = x - cx
            dy = y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Build assignment plan: for each field, pick drones to protect it
        assigned_by_drone = {}
        assigned_set = set()

        # Helper: get a top field delta-sorted list of drones to consider
        if threatened_fields:
            top_field = threatened_fields[0]
            top_group = field_group_map[top_field.id]
            desired_top = desired_by_field.get(top_field.id, 0)

            # Sort drones by distance to top field, with a small bias to keep
            # drones that were protecting the top field previously
            def top_sort_key(d):
                d_to_top = dist_to_field(d, top_field)
                prev_top = (self._prev_assignments.get(d) == top_group)
                # Bias slightly in favor of drones that were already protecting the top field
                bias = -0.01 if prev_top else 0.0
                return (d_to_top + bias)

            if desired_top > 0:
                candidates = sorted(drones, key=top_sort_key)
                for d in candidates[:desired_top]:
                    assigned_by_drone[d] = top_group
                    assigned_set.add(d)

        # For the remaining fields (in threat order), allocate drones similarly
        if threatened_fields:
            for f in threatened_fields[1:]:
                if f.id not in desired_by_field:
                    continue
                need = int(desired_by_field[f.id])
                if need <= 0:
                    continue
                group_id = field_group_map[f.id]

                # Sort by distance to this field, with tie-breaker using previous assignment to that field
                def field_sort_key(d):
                    d_to_field = dist_to_field(d, f)
                    prev_here = (self._prev_assignments.get(d) == group_id)
                    return (d_to_field, -1 if prev_here else 0)

                # Pick drones not already assigned
                candidates = [d for d in drones if d not in assigned_set]
                candidates.sort(key=field_sort_key)

                for d in candidates[:need]:
                    assigned_by_drone[d] = group_id
                    assigned_set.add(d)

        # Any remaining drones go idle
        for d in drones:
            if d not in assigned_set:
                assigned_by_drone[d] = "idle"

        # Apply environment group assignments (explicitly re-assign even if same group)
        for d, grp in assigned_by_drone.items():
            environment.assign_group(d, grp)

        # Update memory of assignments
        new_memory = {}
        for d in drones:
            new_memory[d] = assigned_by_drone.get(d, "idle")
        self._prev_assignments = new_memory
```