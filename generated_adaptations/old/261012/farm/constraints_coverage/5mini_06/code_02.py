from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the single field with the highest threat_level (>0)
        is fully protected using the closest drones. Keep drones already moving
        to or protecting that field. All other drones are set to 'idle'.
        """
        # Helper: compute distance between drone and field center
        def _distance_to_field_center(comp, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = (getattr(comp.location, "x", 0.0) - cx)
            dy = (getattr(comp.location, "y", 0.0) - cy)
            return math.hypot(dx, dy)

        # Collect fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Choose the field with the highest threat_level (tie-break: first)
        highest_field = max(threatened_fields, key=lambda f: f.threat_level)

        protect_group = f"protecting {highest_field.id}"
        # If the protect_group is not valid in group_ids, fallback to idle for safety
        if protect_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Number of drones required for full protection (ensure integer >= 0)
        try:
            required = int(highest_field.drones_for_full_protection)
            if required < 0:
                required = 0
        except Exception:
            required = 0

        # Drones already assigned to this field (either moving_to_field or protecting)
        already_assigned = []
        for comp in components:
            if getattr(comp, "target_id", None) == highest_field.id and getattr(comp, "state", "") in ("moving_to_field", "protecting"):
                already_assigned.append(comp)

        # Determine how many additional drones are needed
        need = max(0, required - len(already_assigned))

        # Build list of candidate drones (those not already assigned to this field)
        candidates = [c for c in components if c not in already_assigned]

        # Sort candidates by distance to the field center
        candidates.sort(key=lambda c: _distance_to_field_center(c, highest_field))

        # Select closest 'need' drones
        selected = candidates[:need] if need > 0 else []

        # Assign groups:
        # - All drones in already_assigned -> protect_group
        # - All drones in selected -> protect_group
        # - All others -> idle
        assigned_to_protect = set(already_assigned) | set(selected)
        for comp in components:
            if comp in assigned_to_protect:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, "idle")