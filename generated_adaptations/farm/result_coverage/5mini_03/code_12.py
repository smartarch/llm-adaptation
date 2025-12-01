from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Protect only the single highest-threat field, using closest drones by estimated arrival time.
        Preference order for recruiting: idle -> moving to other fields -> protecting other fields.
        Keep drones already protecting or moving to the top field. Assign all other drones to 'idle'.
        """
        # Drone speed (units per time); arrival_time = distance / speed
        DRONE_SPEED = 2.0

        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        # Distance from drone to nearest point inside field rectangle
        def distance_to_field_rect(drone, field):
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

        # Find fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats: idle everyone
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Select top field by highest threat_level
        top_field = max(fields, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If group missing, fallback to idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        required = int(getattr(top_field, "drones_for_full_protection", 0))

        comps = list(components)

        # Drones already protecting or moving to the top field
        protecting_top = [c for c in comps if getattr(c, "state", None) == "protecting"
                          and getattr(c, "target_id", None) == top_field.id]
        moving_to_top = [c for c in comps if getattr(c, "state", None) == "moving_to_field"
                         and getattr(c, "target_id", None) == top_field.id and c not in protecting_top]

        # Start with those already committed
        committed = list(protecting_top) + list(moving_to_top)
        committed_set = set(committed)

        current_count = len(committed_set)
        need = max(0, required - current_count)

        # Build candidate buckets excluding those already committed
        idle_candidates = []
        moving_candidates = []
        protecting_candidates = []

        for c in comps:
            if c in committed_set:
                continue
            state = getattr(c, "state", None)
            dist = distance_to_field_rect(c, top_field)
            arrival_time = dist / DRONE_SPEED if DRONE_SPEED > 0 else float('inf')
            if state == "idle":
                idle_candidates.append((arrival_time, c))
            elif state == "moving_to_field":
                # moving to some other field
                moving_candidates.append((arrival_time, c))
            else:
                # state == "protecting" or unknown
                protecting_candidates.append((arrival_time, c))

        # Sort candidates by arrival time (earliest first)
        idle_candidates.sort(key=lambda x: x[0])
        moving_candidates.sort(key=lambda x: x[0])
        protecting_candidates.sort(key=lambda x: x[0])

        # Select additional drones from buckets in order
        selected = []
        if need > 0:
            for bucket in (idle_candidates, moving_candidates, protecting_candidates):
                for atime, c in bucket:
                    selected.append(c)
                    if len(selected) >= need:
                        break
                if len(selected) >= need:
                    break

        # Final protecting set for top field
        final_protecting = set(committed_set).union(selected)

        # Assign chosen drones to protecting group; all others to idle
        for c in comps:
            if c in final_protecting:
                environment.assign_group(c, top_group)
            else:
                environment.assign_group(c, idle_group)