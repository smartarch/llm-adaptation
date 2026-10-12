Reasoning and improved adaptation strategy

Goal refinements you’ve seen in prior iterations:
- The top-threat field must be fully protected using the closest drones, with minimal disruption to existing protections.
- After top-field protection, allocate remaining drones to other threatened fields in threat order, prioritizing proximity and preserving persistence.
- Maintain a protection floor (at least half the drones protecting) when possible, but avoid over-protecting any field.
- Use a memory of past assignments to keep drones in stable roles across ticks, reducing unnecessary movement.

Key new improvements in this version:
- Memory-driven persistence: keep a lightweight mapping of each drone’s last assigned group and reuse it when still valid.
- More disciplined top-field donor selection: we explicitly categorize donors into three pools (idle, en-route to top, and protecting other fields) and displace drones from the least disruptive pool first.
- More conservative secondary-field allocation: only reallocate from fields that are already protecting (and only if they are above their required protection) or from idle drones, with proximity-based selection.
- Clear half-protection floor enforcement with minimal disruption: prioritize top-field protection first, then raise overall protection to the floor using the closest drones, while avoiding unnecessary moves.
- All decisions are made with proximity to the target field to minimize travel time and damage.

Implementation approach:
- Identify threatened fields and sort by threat level (top field first).
- Build an initial assignment using remembered groups for persistence, otherwise infer from current target_id.
- Step 1: Fully protect the top field by pulling from three pools in order: idle, en-route to top, and protecting other fields (only if necessary and as a last resort), always taking the closest first.
- Step 2: Protect other threatened fields by allocating from idle, en-route to some field (not top), and protecting other fields, prioritizing proximity.
- Step 3: Enforce a protection floor: add drones to achieve at least half of the drones protecting, with top-field needs addressed first and using closest drones.
- Step 4: Write final groups to the environment and remember assignments for next tick.

Python code (class SmartFarmAdaptation)

```py
import math
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Simple memory to improve persistence across steps
        self._prev_group_assignments = {}

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones to groups:
        - "idle" for idle drones
        - "protecting {field_id}" for protected fields (one group per field with threat > 0)

        Strategy highlights:
        - Fully protect the top-threat field using the closest drones, counting drones en route to it.
        - Reuse drones from previous groups when still reasonable (persistence).
        - After top field is addressed, protect other threatened fields by proximity and with minimal disruption.
        - Ensure at least half the drones are protecting when possible.
        - Do not over-protect any field beyond drones_for_full_protection.
        - Update internal memory of assignments for next tick.
        """

        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(f)
            return math.hypot(loc.x - cx, loc.y - cy)

        # Gather threatened fields
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, all drones go idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            # Update memory
            self._prev_group_assignments = {d: "idle" for d in components}
            return

        # Sort threatened fields by threat level (desc), top field first
        threatened_fields.sort(key=lambda ff: ff.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Build initial target_group mapping, using previous assignments if valid
        target_group = {}
        prev_mem = getattr(self, "_prev_group_assignments", {}) or {}

        # Prefer previous valid group, else infer from current target
        for d in components:
            prev = prev_mem.get(d)
            if prev in group_ids:
                initial = prev
            else:
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    cand = f"protecting {tid}"
                    if cand in group_ids:
                        initial = cand
                    else:
                        initial = "idle"
                else:
                    initial = "idle"
            target_group[d] = initial

        # Step 1: Fully protect the top field
        # Count current/top-field protection including en-route to top_field
        def is_top_contributor(d):
            if getattr(d, "target_id", None) == top_field.id:
                return True
            if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id:
                return True
            if target_group.get(d, "") == top_group:
                return True
            return False

        current_top_protect = sum(1 for d in components if is_top_contributor(d))
        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)

        if needed_top > 0:
            # Pools prioritized for minimal disruption
            idle = [d for d in components if target_group.get(d, "") == "idle"]
            idle.sort(key=lambda d: dist_to_field(d, top_field))

            enroute_top = [
                d for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id
            ]
            enroute_top.sort(key=lambda d: dist_to_field(d, top_field))

            protecting_others = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) != top_field.id
            ]
            protecting_others.sort(key=lambda d: dist_to_field(d, top_field))

            taken = 0
            pools = [idle, enroute_top, protecting_others]
            for pool in pools:
                for d in pool:
                    if taken >= needed_top:
                        break
                    target_group[d] = top_group
                    taken += 1
                if taken >= needed_top:
                    break

            # If still needed, pull the closest non-top drones toward the top field
            if taken < needed_top:
                remaining_needed = needed_top - taken
                non_top = [d for d in components if target_group.get(d, "") != top_group]
                non_top.sort(key=lambda d: dist_to_field(d, top_field))
                for d in non_top[:remaining_needed]:
                    target_group[d] = top_group
                    taken += 1

        # Step 2: Allocate to other threatened fields (excluding the top field)
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
        required_protecting = (total_drones + 1) // 2
        currently_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))

        if currently_protecting < required_protecting:
            to_gain = required_protecting - currently_protecting

            # First, fill the top field if it still needs protection
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

                if to_gain > 0:
                    # Pull closest non-top drones toward the top field
                    candidates = [d for d in components if target_group.get(d, "") != top_group]
                    candidates.sort(key=lambda d: dist_to_field(d, top_field))
                    for d in candidates:
                        if to_gain <= 0 or top_need <= 0:
                            break
                        target_group[d] = top_group
                        to_gain -= 1
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

        # Update memory for next tick
        self._prev_group_assignments = {d: (target_group.get(d, "idle")) for d in components}
```