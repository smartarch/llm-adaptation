"""
Strategy summary:
- Always fully protect the most threatened field (highest threat_level among fields with threat > 0) by allocating drones until drones_for_full_protection is met.
- Prefer using idle drones first to fill the top field. If idle drones are insufficient, opportunistically reallocate drones that are currently protecting other fields (or even currently en route) to the top field.
- After securing the top field, assign remaining drones to either protect their own target (if still protecting another field) or idle, but ensure every drone ends up in exactly one group this step.
- Drones grouped as "protecting {field_id}" indicate protection of that field. Drones not needed are assigned to "idle".
- We count only drones in state "protecting" toward a field's current protection count (moving_to_field does not count as protection yet).
"""

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

        # Collect threatened fields (threat_level > 0)
        fields = getattr(environment, 'fields', [])
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If nothing threatened, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Determine the most threatened fields (max threat)
        max_threat = max(getattr(f, 'threat_level', 0) for f in threatened_fields)
        top_fields = [f for f in threatened_fields if getattr(f, 'threat_level', 0) == max_threat]

        # Pick the best field among top-threat fields: fewest current protectors (state == 'protecting')
        current_counts = {f.id: 0 for f in top_fields}
        for c in components:
            if getattr(c, 'state', None) == 'protecting':
                tid = getattr(c, 'target_id', None)
                if tid in current_counts:
                    current_counts[tid] += 1

        def id_num(fid):
            try:
                parts = fid.split('_')
                return int(parts[-1])
            except Exception:
                return 0

        best_field = min(
            top_fields,
            key=lambda f: (current_counts.get(f.id, 0), id_num(getattr(f, 'id', 'Field_0')))
        )
        field = best_field
        protect_group = f"protecting {field.id}"

        # Number of drones required for full protection
        required = int(getattr(field, 'drones_for_full_protection', 0))

        # Current protectors for this field (state == 'protecting' and target == field.id)
        current_protectors = [
            c for c in components
            if getattr(c, 'state', None) == 'protecting' and getattr(c, 'target_id', None) == field.id
        ]
        current_for_field = len(current_protectors)

        # Center of the field
        center = ((getattr(field, 'left') + getattr(field, 'right')) / 2.0,
                  (getattr(field, 'top') + getattr(field, 'bottom')) / 2.0)

        # Drones needed to fully protect this field
        needed = max(0, required - current_for_field)

        final_group = {}

        # Keep current protectors on top field
        for c in current_protectors:
            final_group[c] = protect_group

        promoted_from_idle = []
        # Promote idle drones first
        if needed > 0:
            idle_drones = [c for c in components if getattr(c, 'state', None) == 'idle']
            idle_sorted = sorted(idle_drones, key=lambda c: distance2(getattr(c, 'location', None), center))
            for c in idle_sorted[:needed]:
                final_group[c] = protect_group
                promoted_from_idle.append(c)
            needed -= len(promoted_from_idle)

        # If still needed, reallocate drones from other fields (not already top-field protectors)
        if needed > 0:
            # Candidates: drones that are not current_protectors and not already promoted from idle
            candidates = [c for c in components if c not in current_protectors and c not in promoted_from_idle]
            # Sort by distance to the top field center (to minimize movement)
            candidates_sorted = sorted(candidates, key=lambda c: distance2(getattr(c, 'location', None), center))
            for c in candidates_sorted[:needed]:
                final_group[c] = protect_group
            needed = max(0, needed - len(candidates_sorted[:needed]))

        # Remaining drones: if not assigned yet, keep their current targeting or idle
        for c in components:
            if c in final_group:
                continue
            tid = getattr(c, 'target_id', None)
            if tid is not None:
                final_group[c] = f"protecting {tid}"
            else:
                final_group[c] = "idle"

        # Apply final assignment (one group per drone)
        for c, grp in final_group.items():
            environment.assign_group(c, grp)