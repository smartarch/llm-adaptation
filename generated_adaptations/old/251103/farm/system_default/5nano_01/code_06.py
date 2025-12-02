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
            return (getattr(loc, 'x', 0.0), getattr(loc, 'y', 0.0))

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        # Sort threat fields by descending threat level
        threat_fields_sorted = sorted(threat_fields, key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields_sorted[0]
        top_center = center_of(top_field)
        top_required = getattr(top_field, 'drones_for_full_protection', 1)

        # Current protectors for top field (based on current state before reassignment)
        top_current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_field.id]

        # Determine top assignees: those already protecting top + fill if needed
        top_assignees = list(top_current[:top_required])
        if len(top_assignees) < top_required:
            candidates = [d for d in components if d not in top_assignees]
            candidates_sorted = sorted(candidates, key=lambda d: dist(drone_pos(d), top_center))
            needed = top_required - len(top_assignees)
            top_assignees.extend(candidates_sorted[:needed])

        assigned = {}
        for d in top_assignees:
            assigned[d] = f"protecting {top_field.id}"

        # Drones currently protecting top field beyond the required count can help other fields
        extras_top = [d for d in top_current if d not in top_assignees]

        # Remaining pool for allocation to other fields
        used = set(assigned.keys())
        remaining = [d for d in components if d not in used]

        # If there are extras on top, add them to the pool for other fields
        if extras_top:
            remaining.extend(extras_top)

        # Allocate to other fields by threat and proximity
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