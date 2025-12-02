# Reasoning and strategy (embedded as comments for clarity):
# - Goal: further reduce average damage by prioritizing the top-threat field, then distributing remaining drones
#   using a principled, adaptive approach.
# - Steps:
#   1) Identify the top-threat field (highest threat_level). Ensure it has at least drones_for_full_protection protectors.
#      Include both drones currently protecting and those moving toward the top field in this calculation.
#   2) If the top field isn't fully protected yet, bring in the closest available drones to finish the job without
#      evicting drones already heading to or protecting the top field.
#   3) After the top field is fully protected, allocate the remaining drones to secondary threatened fields using a
#      one-by-one greedy marginal-benefit approach:
#        - For each secondary field i, compute needs[i] = drones_for_full_protection - current_protectors (including moving_to_field).
#        - Define a score for field i as threat_level / max(1, needs[i]). Pick the field with the highest score and assign the
#          closest remaining drone to it. Update needs[i] and repeat until all needs are satisfied or no drones remain.
#   4) Drones not assigned to protection become idle. This approach aims to minimize travel time to the top field and
#      allocate remaining resources where they can reduce damage the most.
# - This implementation also accounts for drones in state "moving_to_field" when counting current protectors.

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

        # Build current protectors for each field (including drones heading to field)
        current_by_field = {}
        for f in threat_fields_sorted:
            current_by_field[f.id] = [
                d for d in components
                if getattr(d, 'state', None) in ('protecting', 'moving_to_field')
                and getattr(d, 'target_id', None) == f.id
            ]

        top_protectors = current_by_field[top_field.id]

        assigned = {}

        # Ensure all top_protectors (including moving_to_field) are assigned to top protection
        for d in top_protectors:
            assigned[d] = f"protecting {top_field.id}"

        # If top field is not fully protected yet, bring in closest drones to fill the gap
        if len(top_protectors) < top_required:
            pool = [d for d in components if d not in top_protectors]
            pool_sorted = sorted(pool, key=lambda d: dist(drone_pos(d), top_center))
            needed = top_required - len(top_protectors)
            for i in range(min(needed, len(pool_sorted))):
                d = pool_sorted[i]
                assigned[d] = f"protecting {top_field.id}"

        # Remaining pool for allocation to other fields
        remaining = [d for d in components if d not in assigned]

        # If there are top protectors beyond top_required, we still keep them on top and they stay in assigned above

        # Prepare needs for secondary fields (excluding top)
        needs = {}
        for f in threat_fields_sorted[1:]:
            current = current_by_field[f.id]
            needs[f.id] = max(0, getattr(f, 'drones_for_full_protection', 1) - len(current))

        # Greedy distribution: assign drones one-by-one to secondary fields by marginal benefit
        while remaining:
            # Determine candidate fields with needs > 0
            candidates = [f for f in threat_fields_sorted[1:] if needs.get(f.id, 0) > 0]
            if not candidates:
                break

            # Field with best marginal benefit: higher threat and smaller needs
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

        # Idle any drones not yet assigned
        for d in components:
            if d not in assigned:
                assigned[d] = 'idle'

        # Apply assignments
        for d, group_id in assigned.items():
            environment.assign_group(d, group_id)