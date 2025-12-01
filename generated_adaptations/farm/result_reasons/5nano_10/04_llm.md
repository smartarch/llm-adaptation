Reasoning and improved adaptation strategy

Goal: further reduce drone-driven damage by refining how drones are assigned to field protection groups. The key improvements are:

- Strictly prioritize the top-threat field: ensure it is fully protected using the closest available drones. Drones currently protecting other fields should only be displaced if we cannot reach full protection without doing so, and always by choosing the closest candidates.
- Use proximity-based assignment for other threatened fields: once the top field is addressed, allocate remaining drones to other threatened fields in descending threat order, again prioritizing the closest drones and avoiding unnecessary moves.
- Preserve persistence and avoid over-disruption: drones already protecting a field (or heading to it) are favored to stay; only reassign when it materially improves protection. This supports the requirement that drones shouldn’t change targets too frequently.
- Maintain a protection floor: ensure at least half of the drones are protecting fields whenever possible, reassigning the closest idle or non-top-field drones to protect the fields. This balances active protection with available drones.
- Prevent overprotection: never assign more drones to a field than its drones_for_full_protection, and stop once a field is fully protected.
- Fallback behavior: if no fields are threatened, all drones go idle.

This approach combines a clear priority: top field protection with minimal disruption, followed by secondary field protection using nearby drones, while ensuring a protection baseline and preserving persistence as much as possible.

Python code (class SmartFarmAdaptation)

```py
import math
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones to groups:
        - "idle" for idle drones
        - "protecting {field_id}" for protected fields (one group per field with threat > 0)

        Strategy:
        - Fully protect the most threatened field using the closest drones (prefer drones not already protecting it).
        - Then allocate remaining drones to other threatened fields in threat order,
          always using the closest drones and preserving existing top-field protection when possible.
        - Ensure at least half of the drones are protecting whenever possible, by reallocating from idle or non-top drones.
        - Do not over-protect any field beyond its drones_for_full_protection.
        - Preserve persistence: if a drone is already protecting a field, try to keep it there unless required to protect the top field.
        """

        # Helpers
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def distance_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(f)
            return math.hypot(loc.x - cx, loc.y - cy)

        # Gather threatened fields (threat_level > 0)
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, keep everyone idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level descending (top field first)
        threatened_fields.sort(key=lambda ff: ff.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Build a mapping of current target groups for persistence
        target_group = {}
        for d in components:
            tid = getattr(d, "target_id", None)
            if tid is None:
                target_group[d] = "idle"
            else:
                target_group[d] = f"protecting {tid}"

        # Step 1: Fully protect the top field using the closest available drones
        current_top_protect = sum(1 for d in components if target_group.get(d, "") == top_group)
        need_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        if need_top > 0:
            # Candidates: drones not currently protecting the top field, ordered by distance to top_field
            candidates = [(distance_to_field(d, top_field), d) for d in components if target_group.get(d, "") != top_group]
            candidates.sort(key=lambda t: t[0])

            for _, d in candidates[:need_top]:
                target_group[d] = top_group  # assign to top field

        # Step 2: Allocate to other threatened fields (excluding the top field)
        for f in threatened_fields[1:]:
            group_name = f"protecting {f.id}"
            current = sum(1 for d in components if target_group.get(d, "") == group_name)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue

            # Candidates: drones not already protecting this field or the top field
            candidates = [
                (distance_to_field(d, f), d)
                for d in components
                if target_group.get(d, "") != group_name and target_group.get(d, "") != top_group
            ]
            candidates.sort(key=lambda t: t[0])

            for _, d in candidates[:needed]:
                target_group[d] = group_name

        # Step 3: Ensure at least half the drones are protecting when possible
        total_drones = len(components)
        required_protecting = (total_drones + 1) // 2

        currently_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))
        if currently_protecting < required_protecting:
            to_protect = required_protecting - currently_protecting

            # First, try to add to the top field if it still needs protection
            top_needed = max(0, getattr(top_field, "drones_for_full_protection", 0) - 
                             sum(1 for d in components if target_group.get(d, "") == top_group))
            if top_needed > 0:
                pool = [(distance_to_field(d, top_field), d) for d in components if target_group.get(d, "") != top_group]
                pool.sort(key=lambda t: t[0])
                for _, d in pool[:top_needed]:
                    target_group[d] = top_group
                    currently_protecting += 1
                    to_protect -= 1
                    if to_protect <= 0:
                        break

            # If still short, allocate from other fields/idle, prioritizing the most-threatened remaining fields
            if to_protect > 0:
                for f in threatened_fields[1:]:
                    if to_protect <= 0:
                        break
                    group_name = f"protecting {f.id}"
                    current = sum(1 for d in components if target_group.get(d, "") == group_name)
                    can_add = max(0, getattr(f, "drones_for_full_protection", 0) - current)
                    if can_add <= 0:
                        continue
                    candidates = [(distance_to_field(d, f), d) for d in components if target_group.get(d, "") not in (group_name, top_group)]
                    candidates.sort(key=lambda t: t[0])
                    for _, d in candidates[:can_add]:
                        if to_protect <= 0:
                            break
                        target_group[d] = group_name
                        currently_protecting += 1
                        to_protect -= 1

        # Final: assign groups to environment, ensuring valid group names
        for d in components:
            grp = target_group.get(d, "idle")
            if grp not in group_ids:
                # Fallback: if drone has a target, try to map to that protection group
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    cand = f"protecting {tid}"
                    if cand in group_ids:
                        grp = cand
                    else:
                        grp = "idle"
                else:
                    grp = "idle"
            environment.assign_group(d, grp)

    # Small helper to compute distance (as a method for reuse)
    def _dist(self, drone, field):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.hypot(loc.x - cx, loc.y - cy)
```