from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved adaptation:
    - Always fully protect the highest-threat field using the closest/fastest drones.
    - Treat drones already protecting or already moving to the top field as committed.
    - Strongly discourage reassigning drones that are actively protecting other fields (large penalty).
    - Allocate remaining drones to other fields by a value-per-drone heuristic (threat_level / drones_for_full_protection),
      preserving already-fully-protected fields.
    - Remaining drones become idle.
    """
    DRONE_SPEED = 2.0
    PENALTY_PROTECTING_OTHER = 6.0   # high penalty to avoid stealing protectors
    PENALTY_MOVING_OTHER = 1.0       # mild penalty for drones moving elsewhere

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(ax, ay, bx, by):
            return math.hypot(ax - bx, ay - by)

        def safe_group(name):
            # Return name if present; else fallback to "idle" or first available
            if name in group_ids:
                return name
            if "idle" in group_ids:
                return "idle"
            return group_ids[0] if group_ids else name

        idle_group = safe_group("idle")

        # Gather threatened fields (threat_level > 0) sorted by threat desc, tie-break by id
        threatened_fields = sorted(
            [f for f in environment.fields if getattr(f, "threat_level", 0) > 0],
            key=lambda f: (-f.threat_level, getattr(f, "id", ""))
        )

        # If no threatened fields, set all drones to idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Top (most-threatened) field
        top_field = threatened_fields[0]
        top_group = safe_group(f"protecting {top_field.id}")
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        cx_top, cy_top = field_center(top_field)

        # Remaining drones pool and assignment mapping
        remaining = list(components)
        assignments = {}

        # Helper: estimated arrival time (lower is better). Add penalties for reassigning others.
        def arrival_time_to_field(drone, field, consider_committed_id=None):
            fx, fy = field_center(field)
            lx = getattr(drone.location, "x", 0.0)
            ly = getattr(drone.location, "y", 0.0)
            dist = distance(lx, ly, fx, fy)
            base_time = dist / self.DRONE_SPEED

            # If already protecting this field -> arrival 0 (already there)
            if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) == getattr(field, "id", None):
                return 0.0
            # If moving to this field -> arrival is base_time
            if getattr(drone, "state", None) == "moving_to_field" and getattr(drone, "target_id", None) == getattr(field, "id", None):
                return base_time
            # If protecting another field -> add large penalty
            if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) != getattr(field, "id", None):
                return base_time + self.PENALTY_PROTECTING_OTHER
            # If moving to other field -> small penalty
            if getattr(drone, "state", None) == "moving_to_field" and getattr(drone, "target_id", None) != getattr(field, "id", None):
                return base_time + self.PENALTY_MOVING_OTHER
            # idle or other -> base_time
            return base_time

        # 1) Commit drones already protecting or moving to the top field
        committed_top = []
        for d in list(remaining):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                committed_top.append(d)
                remaining.remove(d)
            elif getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == top_field.id:
                # Treat as committed too (they're en route)
                committed_top.append(d)
                remaining.remove(d)

        # Assign committed to top group (but cap later if more than needed, keep them nevertheless per preference)
        # If there are more committed than required_top, we'll still keep required_top of them assigned to top,
        # and leave extras available for other allocations (but we prefer not to reassign protecting ones).
        # To respect "keep already protecting if fully protected", if committed protectors already satisfy requirement, keep them.
        num_committed = len(committed_top)

        # If committed exceed required_top, pick those already protecting first to remain, then moving ones (stable)
        if num_committed > required_top:
            # prefer to keep actual protectors (state == "protecting") over moving_to_field
            protectors = [d for d in committed_top if getattr(d, "state", None) == "protecting"]
            moving_ones = [d for d in committed_top if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == top_field.id]
            keep = []
            # keep as many protecting as possible
            for d in protectors:
                if len(keep) < required_top:
                    keep.append(d)
            # fill with moving ones if needed
            for d in moving_ones:
                if len(keep) < required_top:
                    keep.append(d)
            # Assign kept ones to top and return extras to remaining pool
            for d in committed_top:
                if d in keep:
                    assignments[d] = top_group
                else:
                    remaining.append(d)
            committed_top = keep
            num_committed = len(committed_top)
        else:
            # assign all committed
            for d in committed_top:
                assignments[d] = top_group

        # 2) If we need more for top field, pick nearest/fastest from remaining (using arrival_time)
        needed_top = max(0, required_top - num_committed)
        if needed_top > 0 and remaining:
            timed = [(d, arrival_time_to_field(d, top_field)) for d in remaining]
            # Tie breaker: prefer idle, then moving_to_field to this field, then moving_to_field, then protecting
            def tie_key(pair):
                d, t = pair
                s = getattr(d, "state", "") or ""
                # rank states to prefer idle and those already heading to top_field (though we removed those earlier)
                rank = 3
                if s == "idle":
                    rank = 0
                elif s == "moving_to_field":
                    # if target is top_field, we would have already removed them; otherwise treat as 1
                    rank = 1
                elif s == "protecting":
                    rank = 4
                return (t, rank)
            timed.sort(key=tie_key)
            pick = [d for d, _t in timed[:needed_top]]
            for d in pick:
                assignments[d] = top_group
                if d in remaining:
                    remaining.remove(d)

        # Ensure top field has required number assigned if possible (if not enough drones exist, assign as many as available)
        # After this point, top field assignments are set in `assignments`.

        # 3) For other fields: preserve already-fully-protected fields (by current protectors), then allocate leftover drones
        # Build list of other fields (exclude top_field) with positive threat
        other_fields = [f for f in threatened_fields if f.id != top_field.id]

        # First preserve existing protectors for other fields: assign drones that are currently protecting that field
        for field in other_fields:
            group_name = safe_group(f"protecting {field.id}")
            if group_name is None:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            existing = [d for d in list(remaining) if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id]
            if len(existing) >= required:
                # Keep exactly required of them assigned (prefer earliest in list)
                for d in existing[:required]:
                    assignments[d] = group_name
                    remaining.remove(d)
                # any extra protectors left in existing beyond required are left in remaining for possible reassignment
            else:
                # Keep all existing (they help), they'll reduce what we need to allocate
                for d in existing:
                    assignments[d] = group_name
                    remaining.remove(d)

        # Now compute a value-per-drone metric for remaining fields to decide allocation order
        # value = threat_level / max(1, drones_for_full_protection), higher means more worth protecting
        field_values = []
        for field in other_fields:
            req = int(getattr(field, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            val = getattr(field, "threat_level", 0.0) / float(max(1, req))
            # also consider how far from being fully protected (residual need): current assigned
            already_assigned = sum(1 for d, g in assignments.items() if g == safe_group(f"protecting {field.id}"))
            residual = max(0, req - already_assigned)
            if residual <= 0:
                continue
            field_values.append((field, val, residual))
        # Sort by value descending (higher priority first), tie-break by threat then id
        field_values.sort(key=lambda x: (-x[1], -getattr(x[0], "threat_level", 0.0), getattr(x[0], "id", "")))

        # Allocate remaining drones greedily to fields by value, picking nearest by arrival time
        for field, _val, residual in field_values:
            if not remaining:
                break
            group_name = safe_group(f"protecting {field.id}")
            # recompute how many still needed (in case assignments changed)
            req = int(getattr(field, "drones_for_full_protection", 0))
            already_assigned = sum(1 for d, g in assignments.items() if g == group_name)
            need = max(0, req - already_assigned)
            if need <= 0:
                continue
            # compute arrival times for remaining drones
            timed = [(d, arrival_time_to_field(d, field)) for d in remaining]
            # prefer drones that are idle and nearby; similar tie-break as earlier
            def tie_key2(pair):
                d, t = pair
                s = getattr(d, "state", "") or ""
                rank = 3
                if s == "idle":
                    rank = 0
                elif s == "moving_to_field":
                    rank = 1
                elif s == "protecting":
                    rank = 4
                return (t, rank)
            timed.sort(key=tie_key2)
            pick = [d for d, _t in timed[:min(need, len(timed))]]
            for d in pick:
                assignments[d] = group_name
                if d in remaining:
                    remaining.remove(d)

        # 4) Any remaining drones become idle
        for d in list(remaining):
            assignments[d] = idle_group
            remaining.remove(d)

        # 5) Apply assignments: ensure every drone is explicitly assigned
        for c in components:
            group = assignments.get(c, idle_group)
            environment.assign_group(c, group)