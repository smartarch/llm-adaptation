from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for smart farm drone allocation.

    - Always fully protect the field with the highest threat_level (>0).
    - Keep drones that are already protecting or moving to that field.
    - Add closest drones until the number required for full protection is reached.
    - All other drones are assigned to "idle".
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between drone and field center
        def _distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Find fields with threat_level > 0
        threatened_fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        idle_group = "idle"

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for comp in components:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    # fallback to first available group if "idle" missing (defensive)
                    environment.assign_group(comp, group_ids[0] if group_ids else idle_group)
            return

        # Choose the field with the highest threat_level (tie-break by field.id for determinism)
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, str(getattr(f, "id", ""))))
        protect_group = f"protecting {target_field.id}" if hasattr(target_field, "id") else None

        # Number of drones required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Determine drones already committed to this field:
        committed = []
        for comp in components:
            # treat protecting or moving_to_field with target_id equal to field id as committed
            if getattr(comp, "target_id", None) == target_field.id and getattr(comp, "state", None) in ("protecting", "moving_to_field"):
                committed.append(comp)

        # If already enough or more than required, keep those committed drones (do not move them),
        # and do not allocate additional drones (extras remain where they are).
        selected_for_protection = list(committed)

        # If we need more drones, choose closest remaining drones
        if len(selected_for_protection) < required:
            needed = required - len(selected_for_protection)
            # Candidates are drones not already in selected_for_protection
            remaining = [c for c in components if c not in selected_for_protection]
            # Sort by distance to the target field center
            remaining.sort(key=lambda c: _distance_to_field_center(c, target_field))
            # Pick up to needed drones
            to_add = remaining[:needed]
            selected_for_protection.extend(to_add)

        # Ensure we don't exceed available drones (selected_for_protection length <= total components)
        # Now assign groups for every drone: protecting group if selected, otherwise idle.
        for comp in components:
            if comp in selected_for_protection and protect_group in group_ids:
                environment.assign_group(comp, protect_group)
            else:
                # assign idle (must exist per spec). If not present, fall back to first available group.
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0] if group_ids else idle_group)