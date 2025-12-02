# Reasoning and adaptation strategy (embedded as comments for one-block delivery):
# - Objective: Improve protection by ensuring the most threatened field is fully protected
#   using the closest available drones, while minimizing unnecessary drone movements.
# - Approach:
#   1) Identify the field with the highest positive threat level.
#   2) If possible, fully protect that field by assigning the minimum number of the closest
#      drones required to reach full protection (considering drones already protecting or
#      en route to that field).
#   3) After securing the top field, allocate any remaining drones to other threatened fields
#      in order of threat, again using the closest drones first to help reach full protection.
#   4) Finally, ensure every drone is assigned to a valid group. If a drone cannot be assigned
#      to a sensible new group, fall back to idle or another valid group.
# - Notes:
#   - The strategy may reassign drones from other fields to the top field if needed to reach full protection.
#   - All assignments are guarded to only use groups present in group_ids.
# - This design aims to reduce average damage by ensuring the top threat is addressed immediately
#   and by making efficient use of all drones, not just idle ones.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields (threat_level > 0)
        fields = getattr(environment, "fields", []) or []
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper: compute field center (used for distance calculations)
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # If there is no threat, idle all drones (fallback to first available group if needed)
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

        # If the top group is not a valid group, idle all drones
        if top_group not in group_ids:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        assigned = set()

        # Step 1: Fully protect the top field using the closest drones
        needed_top = max(
            0,
            getattr(top_field, "drones_for_full_protection", 0)
            - (getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0))
        )

        center_x, center_y = center_of(top_field)

        # Build candidate pool: all drones not already in the top_field protection
        candidates = []
        for d in components:
            # If drone is already protecting this top field, it's effectively counted in protection
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id:
                continue
            if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id:
                continue
            loc = getattr(d, "location", None)
            ifloc_inf = float("inf")
            if loc is not None:
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
                dist = math.hypot(dx - center_x, dy - center_y)
            else:
                dist = ifloc_inf
            candidates.append((dist, d))

        candidates.sort(key=lambda t: t[0])

        top_assigned = []
        if needed_top > 0 and candidates:
            to_take = min(needed_top, len(candidates))
            for i in range(to_take):
                d = candidates[i][1]
                # Guard against invalid group
                if top_group in group_ids:
                    environment.assign_group(d, top_group)
                    assigned.add(d)
                    top_assigned.append(d)

        # If not enough, try to pull from the remaining drones (including those not previously considered)
        still_needed = max(0, needed_top - len(top_assigned))
        if still_needed > 0:
            remaining = []
            for d in components:
                if d in assigned or d in top_assigned:
                    continue
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                    dist = math.hypot(dx - center_x, dy - center_y)
                else:
                    dist = float("inf")
                remaining.append((dist, d))
            remaining.sort(key=lambda t: t[0])
            for _, d in remaining[:still_needed]:
                if top_group in group_ids:
                    environment.assign_group(d, top_group)
                    assigned.add(d)
                    still_needed -= 1
                    if still_needed == 0:
                        break

        # Step 2: After top field is targeted, help other threatened fields using remaining drones
        # Build a pool of drones not yet assigned
        remaining_for_others = []
        for d in components:
            if d in assigned:
                continue
            loc = getattr(d, "location", None)
            if loc is not None:
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
                dist = math.hypot(dx - center_x, dy - center_y)  # distance to top field center as a heuristic
            else:
                dist = float("inf")
            remaining_for_others.append((dist, d))
        remaining_for_others.sort(key=lambda t: t[0])

        # Try to allocate to other threatened fields in threat order
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
            take = min(needed, len(remaining_for_others))
            for i in range(take):
                d = remaining_for_others[i][1]
                environment.assign_group(d, grp)
                assigned.add(d)
            # Remove allocated from pool
            remaining_for_others = remaining_for_others[take:]

        # Step 3: Final safety – ensure every drone has a valid group
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
            # Fallback
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])