import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: squared distance from a drone location to a field center
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

        # Gather fields with threat > 0
        fields = getattr(environment, 'fields', [])
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If nothing threatened, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Find max threat level among threatened fields
        max_threat = max(getattr(f, 'threat_level', 0) for f in threatened_fields)
        # Candidate fields sharing the max threat
        top_fields = [f for f in threatened_fields if getattr(f, 'threat_level', 0) == max_threat]

        # Count how many drones are currently targeting each field (based on target_id)
        current_counts = {f.id: 0 for f in top_fields}
        for c in components:
            tid = getattr(c, 'target_id', None)
            if tid in current_counts:
                current_counts[tid] += 1

        # Pick the best field: highest threat, then fewest current assignees to minimize moves
        best_field = min(top_fields, key=lambda f: current_counts.get(f.id, 0))
        field = best_field
        protect_group = f"protecting {field.id}"

        # Number of drones required for full protection
        required = int(getattr(field, 'drones_for_full_protection', 0))

        # Current number protecting this field (based on target_id)
        current_for_field = int(current_counts.get(field.id, 0))

        # Drones currently targeting this field (by target_id)
        currently_targeting = [c for c in components if getattr(c, 'target_id', None) == field.id]
        currently_set = set(currently_targeting)

        # Drones available to reallocate (not currently targeting this field)
        available = [c for c in components if c not in currently_set]

        # Center of the field
        center = ((getattr(field, 'left') + getattr(field, 'right')) / 2.0,
                  (getattr(field, 'top') + getattr(field, 'bottom')) / 2.0)

        # How many drones we still need to reach full protection
        needed = max(0, required - current_for_field)

        # Sort available drones by proximity to field center
        available_sorted = sorted(available, key=lambda c: distance2(getattr(c, 'location', None), center))

        # Select the closest drones to promote to this field
        to_promote = available_sorted[:min(needed, len(available_sorted))]

        # Promote selected drones to the protection group
        for c in to_promote:
            environment.assign_group(c, protect_group)

        # Ensure all drones currently targeting this field are in the protect group
        for c in currently_targeting:
            environment.assign_group(c, protect_group)

        # All other drones should be idle
        promoted_set = set(to_promote)
        for c in components:
            if c in promoted_set:
                continue
            if c in currently_set:
                continue
            environment.assign_group(c, "idle")