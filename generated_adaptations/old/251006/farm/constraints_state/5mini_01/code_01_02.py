from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Implementation of the adaptation strategy described:
        - Find the field with the highest threat_level (>0).
        - Keep drones already protecting or arriving to that field.
        - If more drones are needed to reach drones_for_full_protection, choose the closest remaining drones.
        - Assign chosen drones to "protecting {field.id}" and all others to "idle".
        """
        # Helper: find valid group name for a protecting field
        def protecting_group_name(field_id):
            return f"protecting {field_id}"

        # Find fields with positive threat
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened field, assign everyone to idle
        if not candidate_fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
            return

        # Choose the field with the highest threat_level (tie-breaker: keep first)
        target_field = max(candidate_fields, key=lambda f: getattr(f, "threat_level", 0))

        # Compute field center for distance calculations
        fx = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        fy = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Number of drones required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Identify drones already protecting or already moving to the target field
        protecting_now = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id]
        arriving_now = [c for c in components if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == target_field.id]

        # Use set of ids (object identity) to track selected drones
        selected = []
        selected_set = set()

        # Add currently protecting and arriving drones first (they count toward required)
        for c in protecting_now + arriving_now:
            if id(c) not in selected_set:
                selected.append(c)
                selected_set.add(id(c))

        # If we still need more, pick closest drones among the rest
        need = max(0, required - len(selected))
        if need > 0:
            # Build list of candidate drones not already selected
            remaining = [c for c in components if id(c) not in selected_set]
            # Sort by Euclidean distance to field center
            remaining.sort(key=lambda c: hypot(getattr(c.location, "x", 0) - fx, getattr(c.location, "y", 0) - fy))
            for c in remaining[:need]:
                selected.append(c)
                selected_set.add(id(c))

        # Determine group names
        protect_group = protecting_group_name(target_field.id)
        protect_group_valid = protect_group in group_ids
        idle_group_valid = "idle" in group_ids

        # Assign groups: selected -> protecting group (if valid), others -> idle
        for c in components:
            if id(c) in selected_set and protect_group_valid:
                environment.assign_group(c, protect_group)
            else:
                # fallback to idle if protecting group not valid or drone not selected
                if idle_group_valid:
                    environment.assign_group(c, "idle")
                else:
                    # As a last resort, try to assign to any protecting group that exists for fields (choose none)
                    # But per spec, "idle" will be present. This branch is defensive.
                    # Assign to first available group_id
                    if group_ids:
                        environment.assign_group(c, group_ids[0])
                    else:
                        # No groups available (unlikely), skip assignment
                        pass