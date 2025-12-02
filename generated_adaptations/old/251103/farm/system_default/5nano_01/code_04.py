# Improved strategy:
# - Do not remove drones from the top field if it's already fully protected.
# - Only move drones away from the top field if we need to add more for top protection to reach the required count.
# - Allocate remaining drones to other fields by proximity to their centers, up to their full-protection needs.
# - Any drone not assigned ends up idle.

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields = getattr(environment, 'fields', [])
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, 'idle')
            return

        # Helpers
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def drone_pos(drone):
            loc = getattr(drone, 'location', None)
            if loc is None:
                return (0.0, 0.0)
            x = getattr(loc, 'x', 0.0)
            y = getattr(loc, 'y', 0.0)
            return (x, y)

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        # Sort threat fields by descending threat level
        threat_fields_sorted = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields_sorted[0]
        top_center = center_of(top_field)
        top_required = getattr(top_field, 'drones_for_full_protection', 1)

        # Current protectors for top field
        top_current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field.id]

        # Drones protecting top field (all of them) will remain protecting top field.
        top_assignees = list(top_current)

        # If top field is not yet fully protected, bring in closest drones to fill the gap
        if len(top_assignees) < top_required:
            candidates = [d for d in components if d not in top_assignees]
            candidates_sorted = sorted(candidates, key=lambda d: dist(drone_pos(d), top_center))
            needed = top_required - len(top_assignees)
            top_assignees.extend(candidates_sorted[:needed])

        # Build final assignment map: drone -> group_id
        assigned = {}

        # Assign top field protection
        for d in top_assignees:
            assigned[d] = f"protecting {top_field.id}"

        # Remaining drones pool (not yet assigned)
        used = set(assigned.keys())
        remaining = [d for d in components if d not in used]

        # Protect other fields (excluding top field) with remaining drones if possible
        for field in threat_fields_sorted[1:]:
            center = center_of(field)
            current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == field.id]
            needed = max(0, getattr(field, 'drones_for_full_protection', 1) - len(current))
            if needed <= 0:
                continue
            if not remaining:
                break
            remaining_sorted = sorted(remaining, key=lambda d: dist(drone_pos(d), center))
            take = min(needed, len(remaining_sorted))
            for i in range(take):
                d = remaining_sorted[i]
                assigned[d] = f"protecting {field.id}"
            remaining = remaining_sorted[take:]

        # Idle any drones not yet assigned
        for d in components:
            if d not in assigned:
                assigned[d] = 'idle'

        # Apply assignments
        for d, group_id in assigned.items():
            environment.assign_group(d, group_id)