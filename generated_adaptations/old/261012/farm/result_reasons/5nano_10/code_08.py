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
        - Fully protect the most threatened field using the closest drones.
          Include drones already protecting it or en route to it in the protection tally.
          Reassign idle drones first, then those en route, then others if needed.
        - After top field is addressed, allocate remaining drones to other threatened fields
          in threat order, using closest drones and avoiding disruption where possible.
        - Ensure at least half the drones are protecting when possible; reallocate closest drones as needed.
        - Do not over-protect any field beyond its drones_for_full_protection.
        - Preserve persistence by preferring drones already protecting or en route to a field.
        """

        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(f)
            return math.hypot(loc.x - cx, loc.y - cy)

        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, keep everyone idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level descending
        threatened_fields.sort(key=lambda ff: ff.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Build current target grouping for persistence
        target_group = {}
        for d in components:
            tid = getattr(d, "target_id", None)
            if tid is None:
                target_group[d] = "idle"
            else:
                target_group[d] = f"protecting {tid}"

        # Step 1: Fully protect the top field
        # Count current/top-field protection including in-transit (moving_to_field) to top field
        current_top_protect = sum(
            1
            for d in components
            if getattr(d, "target_id", None) == top_field.id
        )
        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        if needed_top > 0:
            # Build prioritized candidate lists:
            # 1) idle drones
            idle = [d for d in components if target_group.get(d, "") == "idle"]
            idle.sort(key=lambda d: dist_to_field(d, top_field))

            # 2) drones moving_to_field to the top field
            enroute_top = [
                d for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id
            ]
            enroute_top.sort(key=lambda d: dist_to_field(d, top_field))

            # 3) drones protecting other fields
            protecting_others = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) != top_field.id
            ]
            protecting_others.sort(key=lambda d: dist_to_field(d, top_field))

            # Take from the pooled candidates in order until we fill needed_top
            taken = 0
            for pool in (idle, enroute_top, protecting_others):
                for d in pool:
                    if taken >= needed_top:
                        break
                    # Reassign to top field
                    target_group[d] = top_group
                    taken += 1
                if taken >= needed_top:
                    break

        # Step 2: Allocate to other threatened fields (excluding the top field)
        for f in threatened_fields[1:]:
            gid = f"protecting {f.id}"
            current = sum(1 for d in components if target_group.get(d, "") == gid)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue

            # Candidates: drones not already protecting this field or top field
            candidates = [
                (dist_to_field(d, f), d)
                for d in components
                if target_group.get(d, "") not in (gid, top_group)
            ]
            candidates.sort(key=lambda t: t[0])

            allocated = 0
            for _, d in candidates:
                if allocated >= needed:
                    break
                target_group[d] = gid
                allocated += 1

        # Step 3: Ensure at least half the drones are protecting when possible
        total_drones = len(components)
        required_protecting = (total_drones + 1) // 2
        currently_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))

        if currently_protecting < required_protecting:
            to_gain = required_protecting - currently_protecting

            # First, try to fill top field if it still needs more
            top_current = sum(1 for d in components if target_group.get(d, "") == top_group)
            top_need = max(0, getattr(top_field, "drones_for_full_protection", 0) - top_current)

            if top_need > 0 and to_gain > 0:
                idle = [d for d in components if target_group.get(d, "") == "idle"]
                idle.sort(key=lambda d: dist_to_field(d, top_field))
                for d in idle:
                    if to_gain <= 0 or top_need <= 0:
                        break
                    target_group[d] = top_group
                    to_gain -= 1
                    top_need -= 1
                    currently_protecting += 1

                # If still need to gain, pull closest non-top drones toward the top field
                if to_gain > 0:
                    candidates = [
                        d for d in components if target_group.get(d, "") != top_group
                    ]
                    candidates.sort(key=lambda d: dist_to_field(d, top_field))
                    for d in candidates:
                        if to_gain <= 0 or top_need <= 0:
                            break
                        target_group[d] = top_group
                        to_gain -= 1
                        currently_protecting += 1
                        top_need -= 1

            # If still short, consider other threatened fields that can accept more drones
            if to_gain > 0:
                for f in threatened_fields[1:]:
                    if to_gain <= 0:
                        break
                    gid = f"protecting {f.id}"
                    current = sum(1 for d in components if target_group.get(d, "") == gid)
                    can_add = max(0, getattr(f, "drones_for_full_protection", 0) - current)
                    if can_add <= 0:
                        continue
                    candidates = [
                        (dist_to_field(d, f), d)
                        for d in components
                        if target_group.get(d, "") not in (gid, top_group)
                    ]
                    candidates.sort(key=lambda t: t[0])
                    for _, d in candidates:
                        if to_gain <= 0 or can_add <= 0:
                            break
                        target_group[d] = gid
                        to_gain -= 1
                        currently_protecting += 1
                        can_add -= 1

        # Final: assign groups to environment, ensuring valid group names
        for d in components:
            grp = target_group.get(d, "idle")
            if grp not in group_ids:
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