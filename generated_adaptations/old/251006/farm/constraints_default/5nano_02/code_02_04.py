"""
Adaptive strategy (robust top-field protection):
- Identify the field with the highest threat level (tie-break by id for determinism).
- Ensure the field is fully protected before touching other fields:
  - Preserve drones already protecting this top field.
  - If more drones are needed to reach full protection, reallocate the closest available drones
    (even if they are protecting other fields or idle) to the top field.
  - If there are not enough drones to reach full protection, protect as many as possible.
- All drones not allocated to the top field become idle.
- This strictly prioritizes the most threatened field to reduce immediate damage and minimizes drone movement.
"""

import math
from generated_adaptations.base_classes import farm as base_farm

class SmartFarmAdaptation(base_farm.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no field is threatened, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Select the top-threat field (tie-break by id for determinism)
        top_field = max(fields_with_threat, key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")))
        top_id = getattr(top_field, "id", None)
        top_group = f"protecting {top_id}"

        # Compute the center of the top field
        left = getattr(top_field, "left", 0)
        right = getattr(top_field, "right", 0)
        top = getattr(top_field, "top", 0)
        bottom = getattr(top_field, "bottom", 0)
        top_center = ((left + right) / 2.0, (top + bottom) / 2.0)

        # Drones currently protecting the top field
        current_top = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_id]

        required = int(getattr(top_field, "drones_for_full_protection", 0) or 0)

        final_group = {}

        # If already fully protected, keep those drones and idle the rest
        if len(current_top) >= required:
            for c in components:
                if c in current_top:
                    final_group[c] = top_group
                else:
                    final_group[c] = "idle"
        else:
            # Start with current protectors
            for c in current_top:
                final_group[c] = top_group

            need = max(0, required - len(current_top))

            # Build candidate drones not currently protecting the top field
            candidates = [c for c in components if c not in current_top]

            # Compute distances to the top field center
            cand_with_dist = []
            for c in candidates:
                loc = getattr(c, "location", None)
                if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                    dist = float("inf")
                else:
                    dist = math.hypot(loc.x - top_center[0], loc.y - top_center[1])
                cand_with_dist.append((dist, c))
            cand_with_dist.sort(key=lambda t: t[0])

            allocated = 0
            for dist, c in cand_with_dist:
                if allocated >= need:
                    break
                final_group[c] = top_group
                allocated += 1

            # Any remaining drones become idle
            for dist, c in cand_with_dist[allocated:]:
                final_group[c] = "idle"

        # Apply assignments for all drones (one group per drone)
        for c in components:
            environment.assign_group(c, final_group.get(c, "idle"))