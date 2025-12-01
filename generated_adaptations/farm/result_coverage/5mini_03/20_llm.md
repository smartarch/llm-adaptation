Reasoning and strategy

Goal: further reduce damage while respecting the hard rule — always fully protect the single field with highest threat_level (>0), using the closest drones and keeping drones that already protect it. From previous experiments, stealing protectors is costly; recruiting idle/moving drones quickly is better. Additional fields should only be protected if we can do so quickly without stealing protectors (to avoid churn).

Improvements in this version:
- Use arrival time = distance to nearest point of the field rectangle divided by drone speed (speed = 2) as the primary metric.
- For the top field:
  - Keep drones already protecting/moving to it (unless they are reserved protecting fully-protected fields).
  - Recruit additional drones by smallest arrival time, but penalize stealing protectors (large penalty) to avoid disruption.
- After securing the top field:
  - Attempt to fully protect additional fields (in descending threat) only if:
    - we can do so using only non-protector drones (idle or moving) and
    - the slowest arrival time among the selected drones for that field is below a threshold (MAX_ARRIVAL). This prevents wasting time on distant reassignments that won't help soon.
- Always explicitly assign every drone; drones not used for protection are assigned to "idle".
- Never steal drones from fields that are already fully protected.

The following class implements this strategy.

```py
from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Heuristic:
        - Fully protect the highest-threat field first (must be fully protected).
        - Pick drones minimizing arrival time (distance to rectangle / speed), penalize stealing protectors.
        - After top is secure, try to fully protect other high-threat fields only when they can be reached quickly
          using idle/moving drones (no stealing); this avoids disruptive reassignments.
        - Always explicitly assign every drone.
        """
        DRONE_SPEED = 2.0
        MAX_ARRIVAL_FOR_ADDITIONAL = 12.0  # only commit to other fields if selected drones can arrive quickly

        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        def dist_to_rect(drone, field):
            x = getattr(drone.location, "x", 0)
            y = getattr(drone.location, "y", 0)
            left = getattr(field, "left", 0)
            right = getattr(field, "right", 0)
            top = getattr(field, "top", 0)
            bottom = getattr(field, "bottom", 0)
            nx = clamp(x, left, right)
            ny = clamp(y, top, bottom)
            return hypot(x - nx, y - ny)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else idle_group

        # Gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Helper: protecting group name
        def protect_group(fid):
            g = f"protecting {fid}"
            return g if g in group_ids else None

        comps = list(components)

        # Build maps of protectors and movers per field
        protectors_by_field = {}
        movers_by_field = {}
        for f in fields:
            protectors_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id]
            movers_by_field[f.id] = [c for c in comps if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == f.id]

        # Reserve drones that already fully protect their fields (do not steal)
        reserved = set()
        fully_protected_fields = set()
        for f in fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len(protectors_by_field.get(f.id, []))
            if required > 0 and cur >= required:
                fully_protected_fields.add(f.id)
                for c in protectors_by_field[f.id]:
                    reserved.add(c)

        # Choose top field by highest threat
        top_field = max(fields, key=lambda f: f.threat_level)
        top_grp = protect_group(top_field.id)
        if top_grp is None:
            # Cannot protect (group missing): idle everyone
            for c in comps:
                environment.assign_group(c, idle_group)
            return

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones already protecting or moving to top (exclude those reserved protecting other fully-protected fields)
        protecting_top = [c for c in protectors_by_field.get(top_field.id, []) if c not in reserved]
        moving_top = [c for c in movers_by_field.get(top_field.id, []) if c not in reserved and c not in protecting_top]

        committed_top_set = set(protecting_top + moving_top)
        current_top_count = len(committed_top_set)
        need_top = max(0, required_top - current_top_count)

        # Build candidate list excluding reserved and already committed to top
        candidates = []
        for c in comps:
            if c in reserved or c in committed_top_set:
                continue
            state = getattr(c, "state", None)
            dist = dist_to_rect(c, top_field)
            travel_time = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')
            # Penalize stealing protectors heavily, small penalty for breaking a moving assignment
            if state == "idle":
                penalty = 0.0
            elif state == "moving_to_field":
                penalty = 0.5
            else:
                penalty = 8.0
            adjusted = travel_time + penalty
            candidates.append((adjusted, travel_time, state, c))

        candidates.sort(key=lambda x: x[0])

        selected_for_top = []
        if need_top > 0:
            for adjusted, travel_time, state, c in candidates:
                selected_for_top.append(c)
                if len(selected_for_top) >= need_top:
                    break

        final_top_set = set(protecting_top + moving_top + selected_for_top)

        # Prepare assignment dict and assign reserved protectors to their existing groups
        assignment = {}
        for c in reserved:
            tid = getattr(c, "target_id", None)
            grp = protect_group(tid) or idle_group
            assignment[c] = grp

        for c in final_top_set:
            assignment[c] = top_grp

        # Remaining drones that are not assigned yet
        remaining = [c for c in comps if c not in assignment]

        # Pool for additional fields: only use drones that are idle or moving (do not steal protectors)
        pool = [c for c in remaining if getattr(c, "state", None) in ("idle", "moving_to_field")]

        # Compute needs for other fields (exclude top and fully protected)
        other_fields = [f for f in fields if f.id != top_field.id and f.id not in fully_protected_fields]

        # For each other field, compute current protectors (excluding reserved and those assigned to top)
        def cur_protectors(field):
            return [c for c in protectors_by_field.get(field.id, []) if c not in reserved and c not in final_top_set]

        # Score other fields by threat per needed drone (descending)
        field_candidates = []
        for f in other_fields:
            required = int(getattr(f, "drones_for_full_protection", 0))
            cur = len(cur_protectors(f))
            need = max(0, required - cur)
            if need == 0:
                # keep current protectors assigned
                grp = protect_group(f.id) or idle_group
                for c in cur_protectors(f):
                    assignment[c] = grp
                continue
            score = (f.threat_level / need) if need > 0 else 0
            field_candidates.append((-score, need, f))
        field_candidates.sort()

        # Try to full-protect other fields only if pool contains enough drones and their arrival times are acceptable
        for neg_score, need_f, f in field_candidates:
            if len(pool) < need_f:
                continue
            # select best 'need_f' drones from pool by arrival time to f
            cand = []
            for c in pool:
                dist = dist_to_rect(c, f)
                arrival = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')
                cand.append((arrival, c))
            cand.sort(key=lambda x: x[0])
            chosen = [c for _, c in cand[:need_f]]
            # check slowest arrival among chosen
            slowest = cand[need_f - 1][0] if len(cand) >= need_f else float('inf')
            if slowest <= MAX_ARRIVAL_FOR_ADDITIONAL:
                grp = protect_group(f.id) or idle_group
                for c in chosen:
                    assignment[c] = grp
                # remove chosen from pool and remaining
                pool = [c for c in pool if c not in chosen]
                remaining = [c for c in remaining if c not in chosen]
            # otherwise skip this field (too slow to be worth it)

        # Any remaining drones not assigned: prefer to keep their current protecting/moving assignment if they target a threatened field,
        # otherwise send to idle.
        threatened_ids = {f.id for f in fields}
        for c in remaining:
            state = getattr(c, "state", None)
            tid = getattr(c, "target_id", None)
            if tid in threatened_ids:
                grp = protect_group(tid)
                if grp:
                    assignment[c] = grp
                    continue
            assignment[c] = idle_group

        # Apply assignments (ensure valid group ids)
        for c in comps:
            g = assignment.get(c, idle_group)
            if g not in group_ids:
                g = idle_group
            environment.assign_group(c, g)