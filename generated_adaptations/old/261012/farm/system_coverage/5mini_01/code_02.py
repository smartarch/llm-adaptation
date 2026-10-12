from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that:
    - Finds the field with the highest threat_level (if any > 0).
    - Keeps drones already targeting that field.
    - Adds the closest drones until the field has as many drones as required for full protection.
    - Assigns all other drones to the 'idle' group.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute distance from a component to a point
        def distance_to(comp, x, y):
            lx = getattr(comp.location, "x", 0.0)
            ly = getattr(comp.location, "y", 0.0)
            return math.hypot(lx - x, ly - y)

        # All valid group names are in group_ids; ensure "idle" exists
        idle_group = "idle"
        if idle_group not in group_ids:
            # fallback, though spec says it will be present
            idle_group = group_ids[0] if group_ids else "idle"

        # Find fields with threat_level > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threatened_fields:
            # No threats: assign all drones to idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Select the field with highest threat_level (tie-breaker: use max id for stability)
        primary_field = max(threatened_fields, key=lambda f: (f.threat_level, getattr(f, "id", "")))

        protect_group = f"protecting {primary_field.id}"
        # If the expected protect group does not exist in group_ids, fall back to idle for safety
        if protect_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Determine how many drones are required for full protection
        required = int(getattr(primary_field, "drones_for_full_protection", 0))

        # Identify drones already targeting this field (retain them)
        already_assigned = []
        for comp in components:
            if getattr(comp, "target_id", None) == primary_field.id:
                already_assigned.append(comp)

        assigned_set = set(already_assigned)  # to track which components we've chosen

        # If more are needed, pick the closest available drones
        need = required - len(already_assigned)
        if need > 0:
            cx, cy = field_center(primary_field)
            # Build list of candidate drones not already assigned
            candidates = [comp for comp in components if comp not in assigned_set]
            # Sort candidates by distance to field center
            candidates.sort(key=lambda c: distance_to(c, cx, cy))
            # Pick as many as needed (or as many as available)
            to_add = candidates[:need]
            for comp in to_add:
                assigned_set.add(comp)

        # Now assign groups: assigned_set -> protect_group, others -> idle
        for comp in components:
            if comp in assigned_set:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, idle_group)