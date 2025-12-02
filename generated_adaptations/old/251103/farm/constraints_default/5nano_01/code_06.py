import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # helpers
        def safe_group(name):
            return name if name in group_ids else "idle"

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

        # Gather threatened fields
        fields = getattr(environment, 'fields', [])
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If nothing threatened, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Determine the maximum threat level and candidate top fields
        max_threat = max(getattr(f, 'threat_level', 0) for f in threatened_fields)
        top_fields = [f for f in threatened_fields if getattr(f, 'threat_level', 0) == max_threat]

        # Count current protectors for top fields (based on drones' target_id)
        current_counts = {f.id: 0 for f in top_fields}
        for c in components:
            tid = getattr(c, 'target_id', None)
            if tid in current_counts:
                current_counts[tid] += 1

        # Tie-breaker: among top fields with same threat, pick the one with fewer current protectors,
        # breaking ties by numeric id if possible.
        def id_num(fid):
            try:
                # extract a trailing integer after underscore if present
                parts = fid.split('_')
                return int(parts[-1])
            except Exception:
                return 0

        best_field = min(top_fields, key=lambda f: (current_counts.get(f.id, 0), id_num(getattr(f, 'id', 'Field_0'))))
        field = best_field
        protect_group = safe_group(f"protecting {field.id}")

        # Drones required for full protection
        required = int(getattr(field, 'drones_for_full_protection', 0))

        # Current protectors for this field
        current_for_field = int(current_counts.get(field.id, 0))

        # Drones currently targeting this field
        currently_targeting = [c for c in components if getattr(c, 'target_id', None) == field.id]
        currently_set = set(currently_targeting)

        # Center of the field
        center = ((getattr(field, 'left') + getattr(field, 'right')) / 2.0,
                  (getattr(field, 'top') + getattr(field, 'bottom')) / 2.0)

        # Drones to promote to fill protection (only idle drones considered to minimize disruption)
        needed = max(0, required - current_for_field)

        # Idle drones eligible for promotion
        idle_drones = [c for c in components if getattr(c, 'state', None) == 'idle']

        # Sort idle drones by proximity to field center
        idle_sorted = sorted(idle_drones, key=lambda c: distance2(getattr(c, 'location', None), center))

        to_promote = idle_sorted[:min(needed, len(idle_sorted))]

        # Assign promoted drones to the protection group
        for c in to_promote:
            environment.assign_group(c, protect_group)

        # Ensure currently targeting drones are in the protection group (if group is valid)
        for c in currently_targeting:
            environment.assign_group(c, protect_group)

        # All other drones should be idle (do not disturb existing non-idle drones if they are not needed)
        promoted_set = set(to_promote)
        for c in components:
            if c in promoted_set:
                continue
            if c in currently_set:
                continue
            # No harm in keeping non-top-field protectors as-is if they are already protecting another field.
            # However, to stay aligned with the spec of re-assigning to groups, we keep them idle here.
            environment.assign_group(c, "idle")