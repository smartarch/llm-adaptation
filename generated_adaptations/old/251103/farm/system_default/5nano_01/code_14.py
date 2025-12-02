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

        # Build current protectors for each field (including moving_to_field)
        current_by_field = {}
        for f in threat_fields_sorted:
            current_by_field[f.id] = [
                d for d in components
                if getattr(d, 'state', None) in ('protecting', 'moving_to_field') and getattr(d, 'target_id', None) == f.id
            ]

        top_current = current_by_field[top_field.id]

        assigned = {}

        # Determine top assignees: include drones already protecting or moving to top, up to top_required
        top_protectors = list(top_current)
        top_assignees = top_protectors[:top_required]

        # If top field is not fully protected, bring in closest drones to fill the gap
        if len(top_assignees) < top_required:
            pool = [d for d in components if d not in top_protectors]
            pool_sorted = sorted(pool, key=lambda d: dist(drone_pos(d), top_center))
            needed = top_required - len(top_assignees)
            top_assignees.extend(pool_sorted[:needed])

        # Assign top field protection
        for d in top_assignees:
            assigned[d] = f"protecting {top_field.id}"

        # Drones currently protecting top field beyond what's needed can help other fields
        extras_top = [d for d in top_protectors if d not in top_assignees]

        # Remaining pool for allocation to other fields
        remaining = [d for d in components if d not in assigned]
        if extras_top:
            remaining.extend(extras_top)

        # Prepare needs for secondary fields
        needs = {}
        for f in threat_fields_sorted[1:]:
            current = current_by_field[f.id]
            needed = max(0, getattr(f, 'drones_for_full_protection', 1) - len(current))
            needs[f.id] = needed

        # Greedy distribution: allocate drones to secondary fields by marginal benefit
        # While there are drones and any needs > 0
        while remaining:
            # Build candidate list for fields with needs > 0
            candidates = []
            for f in threat_fields_sorted[1:]:
                if needs.get(f.id, 0) > 0:
                    candidates.append(f)
            if not candidates:
                break

            # Choose the field with the best "threat / needs" score
            def field_score(f):
                n = needs.get(f.id, 0)
                if n <= 0:
                    return -1.0
                return f.threat_level / max(1, n)

            field_to_fill = max(candidates, key=field_score)

            center = center_of(field_to_fill)
            # Pick the closest remaining drone to this field
            best_drone = min(remaining, key=lambda d: dist(drone_pos(d), center))
            assigned[best_drone] = f"protecting {field_to_fill.id}"
            remaining.remove(best_drone)
            needs[field_to_fill.id] -= 1

        # Idle any remaining drones
        for d in remaining:
            assigned[d] = 'idle'

        # Apply assignments
        for d, group_id in assigned.items():
            environment.assign_group(d, group_id)