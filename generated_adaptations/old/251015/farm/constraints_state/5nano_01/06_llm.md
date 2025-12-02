```py
"""
Adaptive strategy update:

- Prioritize the most threatened field (top field) and fully protect it using
  the closest available drones.
- Drones already heading to the top field (moving_to_field or protecting with
  that target) are counted toward protection and kept assigned to the top group.
- If there are more drones needed beyond those, assign the closest unassigned drones.
- After top field protection, allocate any remaining drones to other threatened fields
  in descending threat order, using the same closest-available logic.
- Any drones not assigned to protecting groups are finally set to idle.

This approach guarantees:
- The top field is fully protected when possible.
- Drones are assigned to exactly one group (no duplicates).
- All drones are eventually assigned to a group (idle or protecting).

"""

from math import hypot

# Base class import (as specified)
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Identify threatened fields and select the most threatened one
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        threatened.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = threatened[0]
        top_id = top_field.id

        assigned = set()          # all drones we assign in this run
        assigned_to_top = set()     # drones assigned to protecting top field

        # Step 2: Pre-assign drones already heading to the top field
        for c in components:
            st = getattr(c, "state", "")
            tid = getattr(c, "target_id", None)
            if tid == top_id and st in ("moving_to_field", "protecting"):
                environment.assign_group(c, f"protecting {top_id}")
                assigned.add(c)
                assigned_to_top.add(c)

        # Step 3: Compute how many more drones are needed to fully protect top
        current_protection = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0) + len(assigned_to_top)
        full_protection = int(getattr(top_field, "drones_for_full_protection", 1))
        needed_top = max(0, full_protection - current_protection)

        # Step 4: If more drones are needed, assign the closest unassigned drones to top
        if needed_top > 0:
            center_x = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            center_y = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            candidates = []
            for c in components:
                if c in assigned:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                dist = hypot(dx, dy)
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            for dist, c in candidates:
                if needed_top <= 0:
                    break
                environment.assign_group(c, f"protecting {top_id}")
                assigned.add(c)
                assigned_to_top.add(c)
                needed_top -= 1

        # Step 5: Allocate remaining drones to other threatened fields (if any) in threat order
        remaining_fields = [f for f in threatened if f.id != top_id]
        remaining_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        for f in remaining_fields:
            # Build pool of remaining drones
            pool = [c for c in components if c not in assigned]
            if not pool:
                break

            needed = int(getattr(f, "drones_for_full_protection", 1)) - (getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0))
            needed = max(0, needed)
            if needed <= 0:
                continue

            center_x = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            center_y = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0

            cand = []
            for c in pool:
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                dist = hypot(dx, dy)
                cand.append((dist, c))
            cand.sort(key=lambda t: t[0])

            to_take = min(needed, len(cand))
            for i in range(to_take):
                c = cand[i][1]
                environment.assign_group(c, f"protecting {f.id}")
                assigned.add(c)

        # Step 6: Any drones not assigned yet go idle
        for c in components:
            if c in assigned:
                continue
            environment.assign_group(c, "idle")
```