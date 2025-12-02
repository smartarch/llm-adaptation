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

        # 1) Identify all fields with threat_level > 0, sort by threat (desc)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # If no threat anywhere, all drones idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Prepare final assignment map (one group per drone)
        final_group_for = {c: "idle" for c in components}

        # 3) For each threatened field, compute current protectors and how many more needed
        # We'll try to fully protect fields in order of threat, reusing drones that are already protecting
        remaining_candidates = set(components)  # drones not yet assigned to a protection target
        for field in threatened_fields:
            target_group = f"protecting {field.id}"
            drones_for_full = getattr(field, "drones_for_full_protection", 0)

            # Current protectors for this field
            current = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            current_count = len(current)

            # Mark current protectors to stay in this target group
            for d in current:
                final_group_for[d] = target_group
                if d in remaining_candidates:
                    remaining_candidates.remove(d)

            need = max(0, drones_for_full - current_count)

            if need <= 0:
                continue

            # Choose closest available drones to this field center
            cx, cy = field_center(field)
            # Recompute available pool: those not already assigned to any non-idle group
            candidates = [d for d in remaining_candidates]
            candidates.sort(key=lambda d: dist_to_center(d, cx, cy))

            # Assign up to 'need' drones to this field
            for i in range(min(need, len(candidates))):
                d = candidates[i]
                final_group_for[d] = target_group
                remaining_candidates.remove(d)

        # Helper to compute distance to a field center (for other fields)
        def dist_to_field_center(d, field):
            cx, cy = field_center(field)
            return dist_to_center(d, cx, cy)

        # 4) After trying to fully protect top-threat field, allocate any remaining drones
        # to other threatened fields (in order of threat) if they still require protection
        for field in threatened_fields:
            target_group = f"protecting {field.id}"
            drones_for_full = getattr(field, "drones_for_full_protection", 0)

            # Current protectors for this field (recompute in case previous step updated)
            current = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            current_count = len(current)
            need = max(0, drones_for_full - current_count)
            if need <= 0:
                continue

            cx, cy = field_center(field)
            # Remaining idle drones that can be used for this field
            candidates = [d for d in remaining_candidates]
            candidates.sort(key=lambda d: dist_to_center(d, cx, cy))

            for i in range(min(need, len(candidates))):
                d = candidates[i]
                final_group_for[d] = target_group
                remaining_candidates.remove(d)

        # 5) Apply final assignments (exactly one group per drone)
        for c, grp in final_group_for.items():
            environment.assign_group(c, grp)