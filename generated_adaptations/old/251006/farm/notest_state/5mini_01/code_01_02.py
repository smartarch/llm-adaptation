from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to form group name for a field
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # Find fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, assign all drones to idle
        if not threatened_fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
            return

        # Choose field with highest threat_level
        target_field = max(threatened_fields, key=lambda f: f.threat_level)

        # Compute field center for distance calculations
        cx = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        cy = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Count how many drones are already targeting this field (protecting or moving_to_field)
        already_targeting = [c for c in components if getattr(c, "target_id", None) == target_field.id]
        current_assigned = len(already_targeting)

        # Required total for full protection
        required_total = getattr(target_field, "drones_for_full_protection", 0)

        # How many additional drones we need to send
        needed = max(0, required_total - current_assigned)

        # Candidates: drones not already targeting this field
        candidates = []
        for c in components:
            if getattr(c, "target_id", None) == target_field.id:
                continue
            loc = getattr(c, "location", None)
            if loc is None:
                dist2 = float("inf")
            else:
                dx = (getattr(loc, "x", 0) - cx)
                dy = (getattr(loc, "y", 0) - cy)
                dist2 = dx * dx + dy * dy
            candidates.append((dist2, c))

        # Sort candidates by distance and pick up to 'needed' drones
        candidates.sort(key=lambda x: x[0])
        to_send = set()
        for i in range(min(needed, len(candidates))):
            to_send.add(candidates[i][1])

        # Group name for the chosen field (ensure it exists in group_ids)
        protect_group_name = protecting_group(target_field.id)
        if protect_group_name not in group_ids:
            # Fallback: if group not present, assign all to idle
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
            return

        # Assign groups:
        for comp in components:
            # If the drone already targets the field or is selected to be sent, assign to protect group
            if getattr(comp, "target_id", None) == target_field.id or comp in to_send:
                environment.assign_group(comp, protect_group_name)
            else:
                # Otherwise, idle (use "idle" group if available)
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # If idle group is unexpectedly missing, fallback to some protecting group (shouldn't happen)
                    environment.assign_group(comp, protect_group_name)