import math
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Lightweight persistence memory: last assigned group per drone
        self._prev_group_assignments = {}

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones to groups:
        - "idle" for idle drones
        - "protecting {field_id}" for protected fields (one group per field with threat > 0)
        """

        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(f)
            return math.hypot(loc.x - cx, loc.y - cy)

        # Threatened fields
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing threatened, idle all
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            self._prev_group_assignments = {d: "idle" for d in components}
            return

        # Top field by threat
        threatened_fields.sort(key=lambda ff: ff.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        top_id = top_field.id

        # Initialize target_group using memory when valid
        target_group = {}
        for d in components:
            prev = self._prev_group_assignments.get(d)
            if prev in group_ids:
                initial = prev
            else:
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    cand = f"protecting {tid}"
                    initial = cand if cand in group_ids else "idle"
                else:
                    initial = "idle"
            target_group[d] = initial

        # Helper: know if a drone contributes to top field
        def is_top_contributor(d):
            if getattr(d, "target_id", None) == top_id:
                return True
            if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                return True
            if target_group.get(d, "") == top_group:
                return True
            return False

        # Current protection for top field (count en-route as contributing)
        current_top = sum(1 for d in components if is_top_contributor(d))
        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top)

        # Step 1: Fully protect top field using closest drones (prefer non-disruptive donors)
        if needed_top > 0:
            idle_pool = [d for d in components if target_group.get(d, "") == "idle"]
            idle_pool.sort(key=lambda d: dist_to_field(d, top_field))

            enroute_top = [
                d for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id
            ]
            enroute_top.sort(key=lambda d: dist_to_field(d, top_field))

            protecting_others = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) != top_id
            ]
            protecting_others.sort(key=lambda d: dist_to_field(d, top_field))

            # Donors from over-protected fields (least disruptive)
            # Build current-by-field and capacity maps
            current_by_field = {f.id: sum(1 for d in components if target_group.get(d, "") == f"protecting {f.id}") for f in threatened_fields}
            field_capacity = {f.id: getattr(f, "drones_for_full_protection", 0) for f in threatened_fields}

            donors_over_protected = []
            for fid, cur in current_by_field.items():
                cap = field_capacity.get(fid, 0)
                if cur > cap:
                    # collect drones protecting this field
                    donors_over_protected += [d for d in components if target_group.get(d, "") == f"protecting {fid}"]
            donors_over_protected.sort(key=lambda d: dist_to_field(d, top_field))

            taken = 0
            pools = [idle_pool, enroute_top, protecting_others, donors_over_protected]
            for pool in pools:
                for d in pool:
                    if taken >= needed_top:
                        break
                    target_group[d] = top_group
                    taken += 1
                if taken >= needed_top:
                    break

            if taken < needed_top:
                remaining = needed_top - taken
                non_top = [d for d in components if target_group.get(d, "") != top_group]
                non_top.sort(key=lambda d: dist_to_field(d, top_field))
                for d in non_top[:remaining]:
                    target_group[d] = top_group
                    taken += 1

        # Step 2: Allocate to other threatened fields (excluding top)
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

        # Step 3: Enforce half-protection floor with minimal disruption
        total = len(components)
        required_protecting = (total + 1) // 2
        currently_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))

        if currently_protecting < required_protecting:
            to_gain = required_protecting - currently_protecting

            # First, fill top field if it still needs protection
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

                if to_gain > 0:
                    candidates = [d for d in components if target_group.get(d, "") != top_group]
                    candidates.sort(key=lambda d: dist_to_field(d, top_field))
                    for d in candidates:
                        if to_gain <= 0 or top_need <= 0:
                            break
                        target_group[d] = top_group
                        to_gain -= 1
                        top_need -= 1
                        currently_protecting += 1

            # If still short, pull from over-protected donors (closest first)
            if to_gain > 0:
                # Build current_by_field and capacity again
                current_by_field = {f.id: sum(1 for d in components if target_group.get(d, "") == f"protecting {f.id}") for f in threatened_fields}
                field_capacity = {f.id: getattr(f, "drones_for_full_protection", 0) for f in threatened_fields}
                # Gather donors from any over-protected field (excluding top)
                donors = []
                for d in components:
                    grp = target_group.get(d, "")
                    if grp.startswith("protecting ") and grp != top_group:
                        fid = grp.split(" ", 1)[1]
                        if current_by_field.get(fid, 0) > field_capacity.get(fid, 0):
                            donors.append(d)
                donors.sort(key=lambda d: dist_to_field(d, top_field))
                for d in donors:
                    if to_gain <= 0:
                        break
                    target_group[d] = top_group
                    to_gain -= 1
                    currently_protecting += 1

        # Step 4: Final write-back to environment
        for d in components:
            grp = target_group.get(d, "idle")
            if grp not in group_ids:
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    cand = f"protecting {tid}"
                    grp = cand if cand in group_ids else "idle"
                else:
                    grp = "idle"
            environment.assign_group(d, grp)

        # Update memory for next tick
        self._prev_group_assignments = {d: target_group.get(d, "idle") for d in components}