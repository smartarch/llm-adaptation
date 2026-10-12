from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Find fields with threat_level > 0.
        - Choose the field with the highest threat_level ("target_field").
        - Keep any drone already assigned to that field (target_id == field.id).
        - If more drones are needed to reach field.drones_for_full_protection,
          pick the closest remaining drones to the field center.
        - Assign selected drones to "protecting {field.id}" and assign all others
          to "idle".
        - If no fields have threat_level > 0, assign all drones to "idle".
        """
        # Prepare group name for idle
        idle_group = "idle"
        available_groups = set(group_ids)

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute Euclidean distance
        def dist_sq(a_x, a_y, b_x, b_y):
            dx = a_x - b_x
            dy = a_y - b_y
            return dx * dx + dy * dy

        # Select fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            # No threats: put everyone idle
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        # Choose the field with maximum threat_level (tie-breaker: keep first)
        target_field = max(threat_fields, key=lambda f: f.threat_level)

        protect_group = f"protecting {target_field.id}"
        # Ensure group exists before assigning; if not, fallback to idle for all
        if protect_group not in available_groups:
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))
        # Floor to at least 0
        required = max(0, required)

        # Compute field center once
        cx, cy = field_center(target_field)

        # Classify components: those already committed to this field (by target_id)
        already_assigned = []
        others = []
        for comp in components:
            try:
                comp_target = getattr(comp, "target_id", None)
            except Exception:
                comp_target = None
            if comp_target == target_field.id:
                already_assigned.append(comp)
            else:
                # Compute distance for ordering if needed
                loc = getattr(comp, "location", None)
                if loc is not None:
                    d2 = dist_sq(getattr(loc, "x", 0.0), getattr(loc, "y", 0.0), cx, cy)
                else:
                    d2 = float("inf")
                others.append((d2, comp))

        # Start with keeping already_assigned drones
        selected = list(already_assigned)

        # If not enough, pick closest from others
        if len(selected) < required:
            # sort others by distance squared
            others.sort(key=lambda x: x[0])
            needed = required - len(selected)
            for i in range(min(needed, len(others))):
                selected.append(others[i][1])

        # Now assign groups: selected -> protect_group, rest -> idle_group
        selected_set = set(selected)
        for comp in components:
            if comp in selected_set:
                environment.assign_group(comp, protect_group)
            else:
                # assign to idle if available
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
                else:
                    # If idle group is not available for some reason, try a protecting group
                    # (fallback: no group assignment would violate requirement, but we keep safe)
                    environment.assign_group(comp, protect_group)