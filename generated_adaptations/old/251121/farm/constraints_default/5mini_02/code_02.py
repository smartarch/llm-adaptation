from typing import List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones so that the field with the highest threat_level (if any) is fully protected
        using the closest drones. All other drones are assigned to "idle".
        """
        # Find fields with threat > 0
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatening fields, assign all drones to idle
        if not threat_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Choose the field with the highest threat_level.
        # Tie-break deterministically by field.id (string) to avoid nondeterminism.
        threat_fields.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        target_field = threat_fields[0]

        # Required number of drones for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Compute field center for distance calculations
        center_x = (getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0
        center_y = (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0

        # Identify drones already assigned to this field (by target_id)
        already_assigned = [c for c in components if getattr(c, "target_id", None) == target_field.id]

        # If we already have enough or more, keep them (they will remain assigned)
        num_assigned = len(already_assigned)
        needed = max(0, required - num_assigned)

        # Prepare the list of candidate drones (not already assigned to this field)
        candidates = [c for c in components if c not in already_assigned]

        # Compute distances for candidates and sort by ascending distance
        def dist_to_field(comp):
            loc = getattr(comp, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - center_x
            dy = getattr(loc, "y", 0) - center_y
            return math.hypot(dx, dy)

        candidates.sort(key=dist_to_field)

        # Select nearest needed drones
        selected = already_assigned.copy()
        if needed > 0:
            selected.extend(candidates[:needed])

        # Build set for quick membership test
        selected_set = set(selected)

        # Final group names (ensure exact names are used)
        protecting_group_name = f"protecting {target_field.id}"
        idle_group_name = "idle"

        # Assign every component to either protecting_group_name (if selected) or idle
        for comp in components:
            if comp in selected_set:
                # Assign to the protecting group if that group exists in group_ids (it should)
                if protecting_group_name in group_ids:
                    environment.assign_group(comp, protecting_group_name)
                else:
                    # Fallback: if the protecting group name isn't available, put drone to idle
                    environment.assign_group(comp, idle_group_name)
            else:
                environment.assign_group(comp, idle_group_name)