from __future__ import annotations
import math

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify the field with the highest threat level (>0)
        target_field = None
        max_threat = -1.0
        for field in environment.fields:
            thr = getattr(field, "threat_level", 0.0)
            if thr > 0 and thr > max_threat:
                max_threat = thr
                target_field = field

        # If no threat, set all drones to idle
        if target_field is None:
            for c in components:
                environment.assign_group(c, "idle")
            return

        target_group = f"protecting {target_field.id}"
        drones_for_full = getattr(target_field, "drones_for_full_protection", 0)

        # 2) Count currently protecting drones for the target field
        current_protecting = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id:
                current_protecting += 1

        # 3) Determine how many more drones are needed to reach full protection
        needed_for_target = max(0, drones_for_full - current_protecting)

        # 4) Prepare final assignment: only protect the top-threat field
        final_group_for = {c: "idle" for c in components}

        # a) Keep current protectors on the target field
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id:
                final_group_for[c] = target_group

        # b) If more drones are needed for the target, pick closest available drones
        if needed_for_target > 0:
            center_x = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
            center_y = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

            def dist_to_field(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                return math.hypot(dx, dy)

            # Drones not currently protecting this field
            candidates = [
                d for d in components
                if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_field.id)
            ]
            candidates.sort(key=dist_to_field)

            for i in range(min(needed_for_target, len(candidates))):
                final_group_for[candidates[i]] = target_group

        # 5) Apply final grouping (every drone assigned exactly once)
        for c, grp in final_group_for.items():
            environment.assign_group(c, grp)