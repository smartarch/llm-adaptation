from typing import List
import math

# Import the base class to derive from
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones into groups to protect fields.
        - Idle all drones by default.
        - Identify the field with the highest threat_level (> 0).
        - Use drones to fully protect that field (to its drones_for_full_protection) by assigning
          the closest available drones to its "protecting {field.id}" group.
        - If the field is already fully protected, keep those drones in place (do not move them).
        - All other drones become idle (or can be extended to other fields in future steps).
        """

        # Helper to get the center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Find the top-threat field (with threat_level > 0)
        top_field = None
        top_threat = -1.0
        for f in environment.fields:
            if getattr(f, "threat_level", 0.0) > 0.0:
                if getattr(f, "threat_level", 0.0) > top_threat:
                    top_threat = getattr(f, "threat_level", 0.0)
                    top_field = f

        # If no threatening field, idle all drones
        if top_field is None:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Compute center of the top field
        cx, cy = field_center(top_field)

        # Identify drones currently protecting the top field
        current_protecting = []
        for c in components:
            # If a drone is already protecting this field, keep it in that group
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == top_field.id:
                current_protecting.append(c)

        # Number of drones currently protecting top field
        current_count = len(current_protecting)

        # Desired number of drones for full protection
        desired = int(getattr(top_field, "drones_for_full_protection", 0))

        # If already fully protected, keep those drones and idle the rest
        if current_count >= max(1, desired):
            # Ensure all currently protecting drones stay in the correct group
            for c in current_protecting:
                environment.assign_group(c, f"protecting {top_field.id}")
            # All others go idle
            for c in components:
                if not (getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == top_field.id):
                    environment.assign_group(c, "idle")
            return

        # Drones still needed to reach full protection
        needed = max(0, desired - current_count)

        # Candidates: drones not currently protecting the top field
        candidates = [c for c in components if not (getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == top_field.id)]

        # Compute distance of each candidate to the top field center
        def distance_to_field(c):
            loc = getattr(c, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return math.hypot(dx, dy)

        candidates.sort(key=distance_to_field)

        # Assign the closest 'needed' drones to protect the top field
        assigned = 0
        for c in candidates:
            if assigned >= needed:
                break
            environment.assign_group(c, f"protecting {top_field.id}")
            assigned += 1

        # The rest go idle
        for c in candidates[needed:]:
            environment.assign_group(c, "idle")

        # Ensure already-protecting drones remain in their group
        for c in current_protecting:
            environment.assign_group(c, f"protecting {top_field.id}")