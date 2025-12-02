import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute squared distance between a drone location and a field center
        def distance2(loc, center):
            if loc is None:
                return float('inf')
            x = getattr(loc, 'x', None)
            y = getattr(loc, 'y', None)
            if x is None or y is None:
                return float('inf')
            dx = x - center[0]
            dy = y - center[1]
            return dx * dx + dy * dy

        # Build list of fields with threat_level > 0
        fields = getattr(environment, 'fields', [])
        candidate_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no field is threatened, idle all drones
        if not candidate_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Find the maximum threat level among candidates
        max_threat = max(getattr(f, 'threat_level', 0) for f in candidate_fields)

        # Fields that share the maximum threat level
        top_fields = [f for f in candidate_fields if getattr(f, 'threat_level', 0) == max_threat]

        # Count current protectors for fields in top_fields
        current_counts = {f.id: 0 for f in top_fields}
        for c in components:
            if getattr(c, 'state', None) == 'protecting':
                tid = getattr(c, 'target_id', None)
                if tid in current_counts:
                    current_counts[tid] += 1

        # Pick the best field: the one with max threat and, as tiebreaker, the fewest current protectors
        best_field = min(top_fields, key=lambda f: current_counts.get(f.id, 0))

        field = best_field
        protect_group = f"protecting {field.id}"

        # How many drones are required for full protection
        required = int(getattr(field, 'drones_for_full_protection', 0))

        # Current number of drones protecting this field
        current = int(current_counts.get(field.id, 0))

        # If the field is already fully protected, keep current protectors and idle the rest
        # Determine drones currently protecting this field
        currently_protecting = [c for c in components if getattr(c, 'state', None) == 'protecting' and getattr(c, 'target_id', None) == field.id]
        currently_protecting_set = set(currently_protecting)

        # Drones available to be reallocated (not currently protecting this field)
        available = [c for c in components if c not in currently_protecting_set]

        # Center of the field
        center = ((getattr(field, 'left') + getattr(field, 'right')) / 2.0,
                  (getattr(field, 'top') + getattr(field, 'bottom')) / 2.0)

        # Sort available drones by closeness to field center
        available_sorted = sorted(available, key=lambda c: distance2(getattr(c, 'location', None), center))

        # How many more drones we need to reach full protection
        needed = max(0, required - current)

        # Pick up to 'needed' closest drones to protect the field
        to_promote = available_sorted[:min(needed, len(available_sorted))]

        # Assign promotions to protect_group
        for c in to_promote:
            environment.assign_group(c, protect_group)

        # Ensure currently protecting drones stay in the protect group
        for c in currently_protecting:
            environment.assign_group(c, protect_group)

        # All other drones go idle
        promoted_set = set(to_promote)
        for c in components:
            if c in promoted_set:
                continue
            if c in currently_protecting:
                continue  # already ensured
            environment.assign_group(c, "idle")