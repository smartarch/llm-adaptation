import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into groups:
        - "idle" for drones not protecting the top-threat field
        - "protecting <field_id>" for drones protecting the top-threat field
        The top-threat field is protected to full capacity using the closest available drones.
        """
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, all drones idle
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Select the field with the highest threat level
        top_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        top_group_id = f"protecting {top_field.id}"

        # If the group name isn't in the provided group_ids, fallback to idle gracefully
        if top_group_id not in group_ids:
            top_group_id = "idle"

        # Current protectors for the top field
        current_protectors = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        current_count = len(current_protectors)

        # Number of drones required for full protection
        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Always keep current protectors assigned to the top field
        for d in current_protectors:
            environment.assign_group(d, top_group_id)

        # If more drones are needed, pick closest candidates to the field center
        newly_assigned = []
        if top_field and needed > current_count:
            center_x = (top_field.left + top_field.right) / 2.0
            center_y = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for d in components:
                # Skip those already protecting this top field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = math.hypot(loc.x - center_x, loc.y - center_y)
                else:
                    dist = float("inf")
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            need_more = min(needed - current_count, max(0, len(candidates)))
            for i in range(need_more):
                candidate = candidates[i][1]
                newly_assigned.append(candidate)

        for d in newly_assigned:
            environment.assign_group(d, top_group_id)

        # All remaining drones go idle
        assigned_to_top = set(list(current_protectors) + newly_assigned)
        for d in components:
            if d in assigned_to_top:
                # Already assigned to top_group_id above
                continue
            environment.assign_group(d, "idle")