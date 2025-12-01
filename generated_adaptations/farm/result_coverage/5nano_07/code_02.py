from generated_adaptations.base_classes import farm as base
import math

class SmartFarmAdaptation(base.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Determine fields with threat > 0
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat present, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Pick the field with the highest threat level
        best_field = max(threat_fields, key=lambda f: f.threat_level)

        protect_group = f"protecting {best_field.id}"
        # Safety: ensure the group name exists in group_ids (not strictly required, but keeps consistency)
        if protect_group not in group_ids:
            # If the environment's allowed group_ids don't include this exact string (edge case),
            # fall back to a valid name (though per spec, we should use exact naming).
            protect_group = group_ids[0] if group_ids else protect_group

        required = getattr(best_field, "drones_for_full_protection", 0)

        # Compute current number of drones already protecting this field
        current_protecting = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == best_field.id:
                current_protecting += 1

        # If field has no protection requirement, or we already fully protect it, handle edge cases
        if required <= 0:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # If already fully protected, keep those drones protecting and idle the rest
        if current_protecting >= required:
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == best_field.id:
                    environment.assign_group(c, protect_group)
                else:
                    environment.assign_group(c, "idle")
            return

        # Otherwise, we need to allocate additional drones to reach full protection
        # First, keep existing protectors
        assigned = set()
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == best_field.id:
                environment.assign_group(c, protect_group)
                assigned.add(c)

        # Compute how many more drones we need
        needed = required - current_protecting

        # Prepare list of candidates (not already protecting this field)
        candidates = [c for c in components if c not in assigned]

        # Distance to field center for prioritization
        cx = (getattr(best_field, "left", 0) + getattr(best_field, "right", 0)) / 2.0
        cy = (getattr(best_field, "top", 0) + getattr(best_field, "bottom", 0)) / 2.0

        def dist2_to_field(c):
            loc = getattr(c, "location", None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return dx*dx + dy*dy

        candidates.sort(key=dist2_to_field)

        allocate_now = min(needed, len(candidates))
        for i in range(allocate_now):
            c = candidates[i]
            environment.assign_group(c, protect_group)
            assigned.add(c)

        # All remaining drones go idle
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "idle")