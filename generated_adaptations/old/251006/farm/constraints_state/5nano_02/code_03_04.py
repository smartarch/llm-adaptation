# Strategy rationale embedded as comments:
# - Goal: Always protect the most threatened field first, using the closest drones.
# - Approach:
#   1) Identify the field with the highest positive threat level.
#   2) If possible, fully protect that field by assigning the minimum number of closest drones
#      needed to reach full protection (considering drones already protecting or en route).
#   3) After securing the top field, allocate any remaining drones to other threatened fields
#      in threat order, again using the closest drones first.
#   4) Ensure every drone is assigned to a valid group (idle or a "protecting {field_id}" group).
# - This aims to reduce damage by quickly achieving full protection for the top threat
#   and efficiently using all drones without unnecessary movement.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        fields = getattr(environment, "fields", []) or []
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # If there is no threat, idle all drones (fallback to any valid group)
        if not threatened:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"

        # If the top group isn't a valid group, idle all
        if top_group not in group_ids:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        assigned = set()

        # Step 1: Fully protect the top field if possible
        needed_top = max(
            0,
            getattr(top_field, "drones_for_full_protection", 0)
            - (getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0))
        )

        # Center of the top field
        cx, cy = center_of(top_field)

        # Build list of all drones sorted by distance to top field center
        all_by_dist = []
        for d in components:
            loc = getattr(d, "location", None)
            if loc is not None:
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
                dist = math.hypot(dx - cx, dy - cy)
            else:
                dist = float("inf")
            all_by_dist.append((dist, d))
        all_by_dist.sort(key=lambda t: t[0])

        # Assign the closest drones to the top field as needed
        if needed_top > 0:
            count = min(needed_top, len(all_by_dist))
            for i in range(count):
                d = all_by_dist[i][1]
                environment.assign_group(d, top_group)
                assigned.add(d)

        # Step 2: After top field addressed, help other threatened fields with remaining drones
        # Build a pool of remaining drones (not already assigned to top_group this cycle)
        remaining_for_others = []
        for dist, d in all_by_dist:
            if d in assigned:
                continue
            remaining_for_others.append((dist, d))

        # Allocate to other fields in threat order
        for f in threatened[1:]:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            current = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue
            if not remaining_for_others:
                break
            # Take the closest drones from the pool
            take = min(needed, len(remaining_for_others))
            for i in range(take):
                d = remaining_for_others[i][1]
                environment.assign_group(d, grp)
                assigned.add(d)
            remaining_for_others = remaining_for_others[take:]

        # Step 3: Final safety - ensure every drone has a valid group
        for d in components:
            if d in assigned:
                continue
            st = getattr(d, "state", "")
            tgt = getattr(d, "target_id", None)
            if st == "protecting" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    continue
            if st == "moving_to_field" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    continue
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])