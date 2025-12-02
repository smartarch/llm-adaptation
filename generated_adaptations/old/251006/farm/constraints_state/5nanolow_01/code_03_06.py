from __future__ import annotations
import math

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: distance from drone to a field center
        def field_center(field):
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0
            return cx, cy

        def dist_to_center(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # 1) Identify all threatened fields and sort by threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Prepare final assignments (one group per drone)
        final_group_for = {c: "idle" for c in components}

        # 3) Focus on the most threatened field first
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        drones_for_full = getattr(top_field, "drones_for_full_protection", 0)

        # Current protectors for the top field
        current_top = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id]
        for d in current_top:
            final_group_for[d] = top_group

        needed_top = max(0, drones_for_full - len(current_top))
        if needed_top > 0:
            cx, cy = field_center(top_field)
            candidates = [
                d for d in components
                if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id)
            ]
            candidates.sort(key=lambda d: dist_to_center(d, cx, cy))
            for i in range(min(needed_top, len(candidates))):
                final_group_for[candidates[i]] = top_group

        # 4) After top field, try to assist other threatened fields using remaining idle drones
        # Build list of remaining idle drones
        remaining_idle = [d for d in components if final_group_for[d] == "idle"]

        # Other fields in threat order (excluding the top field)
        other_fields = threatened_fields[1:]
        for field in other_fields:
            field_group = f"protecting {field.id}"
            drones_for_full = getattr(field, "drones_for_full_protection", 0)

            # Current protectors for this field (may have changed earlier)
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id]
            need = max(0, drones_for_full - len(current))
            if need <= 0:
                continue

            cx, cy = field_center(field)
            # Recompute available idle drones
            available = [d for d in remaining_idle if final_group_for[d] == "idle"]
            available.sort(key=lambda d: dist_to_center(d, cx, cy))

            for i in range(min(need, len(available))):
                d = available[i]
                final_group_for[d] = field_group
                remaining_idle.remove(d)

        # 5) Apply final assignments (exactly one group per drone)
        for c, grp in final_group_for.items():
            environment.assign_group(c, grp)