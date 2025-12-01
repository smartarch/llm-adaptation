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

        # Step 0: Top field handling - always allocate the closest drones to fully protect it
        top_field = threatened_fields[0]
        top_center = self._field_center(top_field)

        required_top = min(top_field.drones_for_full_protection, len(components))

        # Distances from all drones to top field center
        drones_with_dist = [(d, self._dist(d.location, top_center)) for d in components]
        drones_with_dist.sort(key=lambda x: x[1])

        # Pick the closest drones to cover top_field
        top_drones = [d for (d, _) in drones_with_dist[:required_top]]

        for d in top_drones:
            final_assignment[d] = f"protecting {top_field.id}"

        # Step 1: Protect remaining threatened fields using remaining drones (closest first)
        remaining_drones = [d for d in components if d not in final_assignment]

        for field in threatened_fields[1:]:
            center = self._field_center(field)
            required = min(field.drones_for_full_protection, len(components))

            if required <= 0:
                continue

            # Distances to this field center for remaining drones
            rem_with_dist = [(d, self._dist(d.location, center)) for d in remaining_drones]
            rem_with_dist.sort(key=lambda x: x[1])

            chosen = [d for (d, _) in rem_with_dist[:required]]

            for d in chosen:
                final_assignment[d] = f"protecting {field.id}"

            # Remove chosen drones from remaining pool
            remaining_drones = [d for d in remaining_drones if d not in chosen]

        # Step 2: Any unmapped drones -> idle
        for d in components:
            if d not in final_assignment:
                final_assignment[d] = "idle"

        # Apply final assignments (exactly once per drone)
        for d, grp in final_assignment.items():
            environment.assign_group(d, grp)