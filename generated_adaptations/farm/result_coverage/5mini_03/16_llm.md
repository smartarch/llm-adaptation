Reasoning and strategy

What I'll change and why:
- The best result so far came from focusing on the single highest-threat field and recruiting drones by estimated arrival time (distance to the field rectangle / speed), preferring idle then moving then protecting. I'll keep that core approach because it performed well.
- Two small but important refinements:
  1. Add an explicit penalty to stealing drones that are currently protecting other fields. This discourages stealing protectors unless absolutely necessary, reducing disruptive reassignments that cause travel delays and larger damage.
  2. Preserve existing assignments for drones that are protecting or moving to other threatened fields (i.e., re-assign them back to their current protecting group) if we didn't recruit them for the top field. This avoids forcing previously-protecting drones to become idle and then re-tasked later; it reduces churn and keeps protections in place when possible.
- Candidate selection still prioritizes idle first, then movers, then protectors, but now uses adjusted arrival time = travel_time + penalty. This should reduce unnecessary stealing while still getting the top field protected quickly.
- All drones must be explicitly assigned each call. Any drone not chosen for the top field and not protecting/moving to a threatened field will be sent to "idle".

Implementation follows.

```py
from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Protect the single highest-threat field using drones chosen by estimated arrival time.
        Penalize stealing protectors to avoid disruptive reassignments.
        Preserve current protecting/moving assignments for other threatened fields when possible.
        """
        DRONE_SPEED = 2.0  # units per time

        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        def distance_to_rect(drone, field):
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

        # Collect threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Choose top field by highest threat_level
        top_field = max(fields, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # Can't assign to protecting group; idle everyone
            for c in components:
                environment.assign_group(c, idle_group)
            return

        required = int(getattr(top_field, "drones_for_full_protection", 0))
        comps = list(components)

        # Identify drones already protecting or moving to the top field
        protecting_top = [c for c in comps if getattr(c, "state", None) == "protecting"
                          and getattr(c, "target_id", None) == top_field.id]
        moving_to_top = [c for c in comps if getattr(c, "state", None) == "moving_to_field"
                         and getattr(c, "target_id", None) == top_field.id and c not in protecting_top]

        committed = set(protecting_top + moving_to_top)
        current_count = len(committed)
        need = max(0, required - current_count)

        # Build list of threatened ids (for preserving other assignments)
        threatened_ids = {f.id for f in fields}

        # Candidate drones (not already committed to top)
        candidates = []
        for c in comps:
            if c in committed:
                continue
            state = getattr(c, "state", None)
            dist = distance_to_rect(c, top_field)
            travel_time = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')

            # Penalty to avoid stealing protectors (seconds)
            if state == "idle":
                penalty = 0.0
            elif state == "moving_to_field":
                penalty = 0.5  # small penalty for breaking a moving assignment
            else:
                # protecting: larger penalty (discourage stealing)
                penalty = 6.0

            adjusted_time = travel_time + penalty
            candidates.append((adjusted_time, state, c))

        # Sort by adjusted time (ascending)
        candidates.sort(key=lambda x: x[0])

        # Select needed drones from candidates
        selected = []
        if need > 0:
            for adjusted_time, state, c in candidates:
                selected.append(c)
                if len(selected) >= need:
                    break

        final_protecting_top = committed.union(selected)

        # Now assign groups:
        # - Drones in final_protecting_top -> protect top_group
        # - For other drones:
        #     if currently protecting a threatened field -> assign protecting {target_id}
        #     elif moving_to_field to a threatened field -> assign protecting {target_id}
        #     else -> idle

        for c in comps:
            if c in final_protecting_top:
                environment.assign_group(c, top_group)
                continue

            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)

            if target in threatened_ids:
                grp = f"protecting {target}"
                if grp in group_ids:
                    environment.assign_group(c, grp)
                    continue

            # Fallback: idle
            environment.assign_group(c, idle_group)