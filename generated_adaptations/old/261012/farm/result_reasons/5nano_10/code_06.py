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

        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort by threat level descending
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

        # Count current/progress toward top field
        current_top_protect = 0
        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if tid == top_field.id:
                if st == "protecting":
                    current_top_protect += 1
                elif st == "moving_to_field":
                    current_top_protect += 1  # treat in-transit as contributing

        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        # Step 1: Fully protect the top field
        if needed_top > 0:
            # Build candidates ordered by desirability to reassign
            candidates = []
            for d in components:
                if target_group.get(d, "") == top_group:
                    continue
                # We consider all drones except those already in top_group
                # Prioritize idle, then en route, then others (via distance)
                candidates.append((dist_to_field(d, top_field), d))

            candidates.sort(key=lambda t: t[0])
            # Take the closest needed_top drones
            taken = 0
            for _, d in candidates:
                if taken >= needed_top:
                    break
                target_group[d] = top_group
                taken += 1

        # Step 2: Allocate to other threatened fields (not the top field)
        for f in threatened_fields[1:]:
            gid = f"protecting {f.id}"
            current = sum(1 for d in components if target_group.get(d, "") == gid)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue

            candidates = []
            for d in components:
                if target_group.get(d, "") in (gid, top_group):
                    continue
                candidates.append((dist_to_field(d, f), d))
            candidates.sort(key=lambda t: t[0])

            allocated = 0
            for _, d in candidates:
                if allocated >= needed:
                    break
                target_group[d] = gid
                allocated += 1

        # Step 3: Ensure at least half the drones are protecting when possible
        total_drones = len(components)
        required_protecting = (total_drones + 1) // 2  # ceil

        currently_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))
        if currently_protecting < required_protecting:
            to_gain = required_protecting - currently_protecting

            # First prefer idle drones
            idle_candidates = [d for d in components if target_group.get(d, "") == "idle"]
            idle_candidates.sort(key=lambda d: dist_to_field(d, top_field))

            for d in idle_candidates:
                if to_gain <= 0:
                    break
                target_group[d] = top_group
                to_gain -= 1
                currently_protecting += 1

            # If still short, pull from drones not in the top group, closest to the top field
            if to_gain > 0:
                others = [d for d in components if target_group.get(d, "") != top_group]
                others.sort(key=lambda d: dist_to_field(d, top_field))
                for d in others:
                    if to_gain <= 0:
                        break
                    target_group[d] = top_group
                    to_gain -= 1
                    currently_protecting += 1

        # Final: assign groups to environment (valid group names)
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