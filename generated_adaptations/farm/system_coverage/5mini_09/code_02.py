from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _distance_to_field(self, drone_loc, field):
        # Compute shortest Euclidean distance from a point to a rectangle
        x = drone_loc.x
        y = drone_loc.y
        # rectangle bounds
        left, right = field.left, field.right
        top, bottom = field.top, field.bottom

        # distance along x
        if left <= x <= right:
            dx = 0.0
        else:
            dx = min(abs(x - left), abs(x - right))
        # distance along y
        if top <= y <= bottom:
            dy = 0.0
        else:
            dy = min(abs(y - top), abs(y - bottom))
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare group name for idle
        idle_group = "idle"
        # Find fields with threat_level > 0
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]

        if not threatened_fields:
            # No threats: assign all drones to idle
            for c in components:
                target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else None)
                if target is not None:
                    environment.assign_group(c, target)
            return

        # Pick the field with the highest threat level (tie-breaker: keep first)
        highest = max(threatened_fields, key=lambda f: f.threat_level)
        protect_group = f"protecting {highest.id}"
        # Fallback if protect_group not in group_ids (shouldn't happen per spec)
        if protect_group not in group_ids:
            protect_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else None)

        required = int(highest.drones_for_full_protection)

        # Identify drones already committed to this field (protecting or moving_to_field)
        committed = []
        uncommitted = []
        for c in components:
            if c.target_id == highest.id and c.state in ("protecting", "moving_to_field"):
                committed.append(c)
            else:
                uncommitted.append(c)

        committed_count = len(committed)

        # Determine how many additional drones are needed
        need_more = max(0, required - committed_count)

        # Sort uncommitted drones by distance to the target field
        uncommitted_sorted = sorted(uncommitted, key=lambda d: self._distance_to_field(d.location, highest))

        # Select additional drones to commit
        to_commit = uncommitted_sorted[:need_more]
        remaining_after_commit = uncommitted_sorted[need_more:]

        # Assign committed and newly committed drones to protecting group
        for c in committed:
            environment.assign_group(c, protect_group)
        for c in to_commit:
            environment.assign_group(c, protect_group)

        # All other drones -> idle (or safe fallback)
        idle_target = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else None)
        for c in remaining_after_commit:
            if idle_target is not None:
                environment.assign_group(c, idle_target)
        # Ensure any components that somehow weren't handled (unlikely) are assigned
        # (This also covers components list elements not present in our splits)
        handled = set(committed) | set(to_commit) | set(remaining_after_commit)
        for c in components:
            if c not in handled:
                final_target = protect_group if (c.target_id == highest.id and protect_group in group_ids) else idle_target
                if final_target is not None:
                    environment.assign_group(c, final_target)