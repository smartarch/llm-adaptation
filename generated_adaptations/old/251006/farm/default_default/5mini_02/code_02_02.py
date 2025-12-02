"""
SmartFarmAdaptation

Reasoning and improved strategy:

Goal (mandatory): Always fully protect the single field with the highest threat_level
(using the exact protecting group "protecting {field.id}"). Use as many drones as
required for full protection (drones_for_full_protection), and explicitly assign each
drone to a group every step.

Observed problems with the earlier approach:
- The highest-threat field often ended up under-covered (coverage ~0.6). This suggests
  that the selection of drones to reassign did not sufficiently prioritize drones that
  could arrive quickly or it avoided pulling drones from places that still needed them.
- We must aggressively ensure the highest-threat field gets full protection even if that
  requires redistributing drones. To reduce time-to-protect, we should select drones
  based on estimated arrival time (distance / speed), not just raw distance squared.

Improved strategy:
1. Identify the single highest-threat field (tie-broken by id for determinism).
2. Count drones already committed to that field (target_id == field.id). These remain assigned.
3. Compute how many additional drones are needed (needed_remaining).
4. Build a prioritized candidate pool of other drones to move to the highest field:
   - Priority 0: idle drones (target_id is None) — least disruptive to reassign.
   - Priority 1: drones assigned to other fields that have a surplus (assigned > required).
                 We can steal surplus without leaving those fields unprotected.
   - Priority 2: drones assigned to other threatened fields without surplus — we try these
                 only if needed.
   For each candidate compute estimated arrival_time = distance_to_field_center / drone_speed.
   Drone speed is specified as 2 in the problem, so arrival_time = distance / 2.
5. Sort candidates by (priority, arrival_time) and pick the top needed_remaining drones.
   This favors drones that can arrive quickly and are least disruptive to reassign.
6. Assign:
   - All drones committed to the highest field and the selected candidates -> "protecting {hf.id}".
   - Any other drone whose current target corresponds to another threatened field -> keep protecting that field.
   - All remaining drones -> "idle".
7. Always use only group names provided in group_ids. If "idle" or an expected protecting group
   is missing, fall back to the first provided group (rare).

This approach reduces time-to-protect by choosing drones that can reach the highest-threat field fastest
and by preferring idle/surplus drones before pulling from currently under-protected fields.

The code below implements this strategy. All reasoning above is included here as comments.
"""

from typing import List, Dict
from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List[object], environment: object, group_ids: List[str], step: int):
        # Helper to compute field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Drone movement speed (given in problem)
        DRONE_SPEED = 2.0

        # Build mapping of protecting group names for threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        protecting_group_for_field: Dict[str, str] = {}
        for f in threatened_fields:
            gname = f"protecting {f.id}"
            if gname in group_ids:
                protecting_group_for_field[f.id] = gname

        # If no threatened fields (or no protecting groups available), assign all drones to idle
        if not protecting_group_for_field:
            idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Select the highest-threat field (tie-break by id)
        def fld_key(f):
            return (f.threat_level, f.id)
        highest_field = max(threatened_fields, key=fld_key)
        highest_group = protecting_group_for_field.get(highest_field.id, None)

        # Precompute field centers
        hf_cx, hf_cy = field_center(highest_field)

        # Build mapping: target_id -> list of drones currently targeting that field (or None)
        assigned_by_field: Dict[str, List[object]] = {}
        idle_drones: List[object] = []
        for c in components:
            tgt = getattr(c, "target_id", None)
            if tgt is None:
                idle_drones.append(c)
            else:
                assigned_by_field.setdefault(tgt, []).append(c)

        # Drones already committed to highest field
        committed = assigned_by_field.get(highest_field.id, [])
        committed_ids = set(id(d) for d in committed)

        # Number required for full protection
        required = int(getattr(highest_field, "drones_for_full_protection", 0))
        current_committed = len(committed)
        needed_remaining = max(0, required - current_committed)

        # If no extra drones needed, just keep committed drones at highest, keep others where they are (or idle)
        if needed_remaining <= 0:
            for c in components:
                if id(c) in committed_ids and highest_group is not None:
                    environment.assign_group(c, highest_group)
                else:
                    # keep protecting current target if it's a threatened field and group exists
                    t = getattr(c, "target_id", None)
                    if t in protecting_group_for_field:
                        environment.assign_group(c, protecting_group_for_field[t])
                    else:
                        # otherwise idle
                        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                        environment.assign_group(c, idle_group)
            return

        # Build candidate list with priorities
        # Priority 0: idle drones
        # Priority 1: drones from other fields that have surplus (assigned > required_for_that_field)
        # Priority 2: drones from other threatened fields without surplus
        candidates = []  # tuples (priority, arrival_time, comp)

        # Add idle drones (priority 0)
        for c in idle_drones:
            try:
                dx = float(c.location.x) - hf_cx
                dy = float(c.location.y) - hf_cy
                dist = sqrt(dx * dx + dy * dy)
            except Exception:
                dist = float("inf")
            arrival = dist / DRONE_SPEED
            candidates.append((0, arrival, c))

        # For threatened fields, compute their assigned counts and surplus
        field_assigned_count: Dict[str, int] = {}
        for f in threatened_fields:
            field_assigned_count[f.id] = len(assigned_by_field.get(f.id, []))

        # For drones assigned to other fields, categorize
        for f in threatened_fields:
            if f.id == highest_field.id:
                continue
            assigned_list = assigned_by_field.get(f.id, [])
            required_f = int(getattr(f, "drones_for_full_protection", 0))
            surplus = max(0, len(assigned_list) - required_f)
            # For each drone in assigned_list, set priority based on whether surplus > 0
            # For deterministic behavior, sort assigned_list by distance to highest (closer first)
            temp = []
            for c in assigned_list:
                try:
                    dx = float(c.location.x) - hf_cx
                    dy = float(c.location.y) - hf_cy
                    dist = sqrt(dx * dx + dy * dy)
                except Exception:
                    dist = float("inf")
                arrival = dist / DRONE_SPEED
                temp.append((arrival, c))
            temp.sort(key=lambda x: x[0])
            # Assign priority 1 to as many as surplus, then priority 2 to the rest
            for idx, (arrival, c) in enumerate(temp):
                prio = 1 if idx < surplus else 2
                candidates.append((prio, arrival, c))

        # Also consider drones assigned to non-threatened fields (if any). They are lower priority than surplus.
        # Note: assigned_by_field may contain keys for non-threatened fields; include them with priority 2.
        for tgt, lst in assigned_by_field.items():
            if tgt in field_assigned_count or tgt == highest_field.id:
                continue
            for c in lst:
                try:
                    dx = float(c.location.x) - hf_cx
                    dy = float(c.location.y) - hf_cy
                    dist = sqrt(dx * dx + dy * dy)
                except Exception:
                    dist = float("inf")
                arrival = dist / DRONE_SPEED
                candidates.append((2, arrival, c))

        # Exclude drones already committed to highest (we counted them already)
        candidates = [(p, a, c) for (p, a, c) in candidates if id(c) not in committed_ids]

        # Sort candidates by (priority, arrival_time) and pick needed_remaining
        candidates.sort(key=lambda x: (x[0], x[1], id(x[2])))
        selected_for_highest = set()
        for i in range(min(needed_remaining, len(candidates))):
            _, _, comp = candidates[i]
            selected_for_highest.add(id(comp))

        # If we still didn't get enough (unlikely), pick any remaining drones by arrival time irrespective of priority
        if len(selected_for_highest) < needed_remaining:
            # find any other drones not yet selected and not committed
            remaining = [c for c in components if id(c) not in committed_ids and id(c) not in selected_for_highest]
            rem_list = []
            for c in remaining:
                try:
                    dx = float(c.location.x) - hf_cx
                    dy = float(c.location.y) - hf_cy
                    dist = sqrt(dx * dx + dy * dy)
                except Exception:
                    dist = float("inf")
                arrival = dist / DRONE_SPEED
                rem_list.append((arrival, c))
            rem_list.sort(key=lambda x: (x[0], id(x[1])))
            need_more = needed_remaining - len(selected_for_highest)
            for i in range(min(need_more, len(rem_list))):
                _, comp = rem_list[i]
                selected_for_highest.add(id(comp))

        # Final assignment: each drone must be explicitly assigned to one group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
        for c in components:
            cid = id(c)
            # If committed to highest or selected to go there -> assign to highest_group
            if cid in committed_ids and highest_group is not None:
                environment.assign_group(c, highest_group)
            elif cid in selected_for_highest and highest_group is not None:
                environment.assign_group(c, highest_group)
            else:
                # Keep drones protecting their current (threatened) target if possible
                tgt = getattr(c, "target_id", None)
                if tgt in protecting_group_for_field:
                    environment.assign_group(c, protecting_group_for_field[tgt])
                else:
                    environment.assign_group(c, idle_group)