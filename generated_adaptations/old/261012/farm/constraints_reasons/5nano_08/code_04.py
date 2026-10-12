import math
from typing import List

# Assuming the base class is importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        class P:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        return P(cx, cy)

    def assign_drones(self, components: List, environment, group_ids, step: int):
        """
        Distribute drones among fields to maximize protection.
        Components: drones with attributes state, target_id, location (with x, y).
        environment.fields: field objects with id, left, top, right, bottom, threat_level, drones_for_full_protection
        Use environment.assign_group(component, group_id) to assign a drone.
        """

        # Gather threatened fields (threat_level > 0)
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat_level desc (most threatened first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Build final assignment map: drone -> group_id
        final_assignment = {}

        # Helper to assign a drone if not already assigned (idempotent in our single-pass approach)
        def set_group(drone, group_id):
            final_assignment[drone] = group_id

        # Step 0: Top field handling
        top_field = threatened_fields[0]
        top_center = self._field_center(top_field)

        # Drones currently protecting the top field
        top_current = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id]

        required_top = min(top_field.drones_for_full_protection, len(components))

        # Sort current top protectors by distance to top center (closest first)
        top_current_sorted = sorted(top_current, key=lambda d: self._dist(d.location, top_center))

        # If there are more current protectors than required, keep the closest ones and move the rest to idle
        keep_top = min(len(top_current_sorted), required_top)
        for i in range(keep_top):
            set_group(top_current_sorted[i], f"protecting {top_field.id}")
        for d in top_current_sorted[keep_top:]:
            # mark to idle
            set_group(d, "idle")

        deficit_top = max(0, required_top - keep_top)

        if deficit_top > 0:
            # Candidates: all drones not already assigned to top field
            candidates = [d for d in components if d not in final_assignment]
            candidates.sort(key=lambda d: self._dist(d.location, top_center))
            for i in range(min(deficit_top, len(candidates))):
                set_group(candidates[i], f"protecting {top_field.id}")

        # Step 1: Other threatened fields
        for f in threatened_fields[1:]:
            center_f = self._field_center(f)

            # Current protectors for this field
            curr = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == f.id]
            curr_sorted = sorted(curr, key=lambda d: self._dist(d.location, center_f))

            required = min(f.drones_for_full_protection, len(components))
            keep = min(len(curr_sorted), required)

            # Keep closest current protectors
            for i in range(keep):
                set_group(curr_sorted[i], f"protecting {f.id}")

            # Others currently protecting this field (excess) become idle
            for d in curr_sorted[keep:]:
                set_group(d, "idle")

            deficit = max(0, required - keep)

            if deficit > 0:
                candidates = [d for d in components if d not in final_assignment]
                candidates.sort(key=lambda d: self._dist(d.location, center_f))
                for i in range(min(deficit, len(candidates))):
                    set_group(candidates[i], f"protecting {f.id}")

        # Step 2: Any unmapped drones -> idle
        for d in components:
            if d not in final_assignment:
                set_group(d, "idle")

        # Apply final assignments (exactly once per drone)
        for d, grp in final_assignment.items():
            environment.assign_group(d, grp)