from math import ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the field with highest threat_level is fully protected
        using the closest drones. Keep drones already protecting that field in place.
        All other drones are assigned to 'idle'.
        """
        # Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no field needs protection, make all drones idle
        if not threat_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Select the field with highest threat_level
        target_field = max(threat_fields, key=lambda f: f.threat_level)
        protect_group = f"protecting {target_field.id}"

        # Safety: if the expected protect_group isn't in group_ids, fallback to idle assignments
        if protect_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Compute field center for distance calculations
        cx = (target_field.left + target_field.right) / 2.0
        cy = (target_field.top + target_field.bottom) / 2.0

        # Identify drones already protecting this field (they count toward full protection)
        currently_protecting = [
            c for c in components
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id
        ]

        current_protect_count = len(currently_protecting)
        required_total = int(ceil(getattr(target_field, "drones_for_full_protection", 0)))
        needed = max(0, required_total - current_protect_count)

        # Helper to compute squared distance to field center
        def dist2(comp):
            lx = getattr(comp, "location").x
            ly = getattr(comp, "location").y
            dx = lx - cx
            dy = ly - cy
            return dx * dx + dy * dy

        # Candidates are all drones not already counted as currently_protecting
        candidates = [c for c in components if c not in currently_protecting]

        # Sort candidates: prefer those already moving_to_field toward this field, then by distance
        def candidate_key(c):
            pref = 0 if (getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == target_field.id) else 1
            return (pref, dist2(c))

        candidates.sort(key=candidate_key)

        # Select as many closest candidates as needed (or all if not enough)
        selected = set(candidates[:needed]) if needed > 0 else set()

        # Assign groups: keep current protectors and selected candidates on protecting group; others idle
        for comp in components:
            if comp in selected or comp in currently_protecting:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, "idle")