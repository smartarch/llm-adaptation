"""
Adaptive strategy improvement:
- Focus on fully protecting the most threatened field first.
- If its protection group exists, allocate the closest drones to that field until
  drones_for_full_protection is met. Drones currently protecting that field remain there.
- After topping the most-threatened field, allocate remaining drones to other threatened fields
  (in threat order) by reassigning from any drones not already protecting the target field.
- Always end with exactly one environment.assign_group call per drone.
"""
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields
        threatened_fields = [
            f for f in environment.fields if getattr(f, "threat_level", 0) > 0
        ]

        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # If the top group's not available, fall back to idle for all
        if top_group not in group_ids:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Build final assignment mapping (start with all idle)
        final_group = {d: "idle" for d in components}

        # Phase 1: Top field protection
        current_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        for d in current_top:
            final_group[d] = top_group

        current_count = len(current_top)
        needed_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)) - current_count)

        if needed_top > 0:
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Candidates: any drone not currently in the top group
            candidates = []
            top_set = set(current_top)
            for d in components:
                if d in top_set:
                    continue
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed_top, len(candidates))):
                drone = candidates[i][1]
                final_group[drone] = top_group

        # Phase 2: Allocate remaining drones to other threatened fields
        for field in threatened_fields[1:]:
            group = f"protecting {field.id}"
            if group not in group_ids:
                continue

            # Current protectors for this field
            current_protectors = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            for d in current_protectors:
                final_group[d] = group

            needed = max(0, int(getattr(field, "drones_for_full_protection", 0)) - len(current_protectors))
            if needed <= 0:
                continue

            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            candidates = []
            current_set = set(current_protectors)
            for d in components:
                if d in current_set:
                    continue
                # Can reallocate any drone not already in this target group
                if final_group[d] == group:
                    continue
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group[drone] = group

        # Phase 3: Assign exactly one group per drone
        for d in components:
            environment.assign_group(d, final_group[d])