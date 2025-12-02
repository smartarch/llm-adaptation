from typing import List
import abc

# Assuming this import path based on problem statement
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        components: list of drone components
        environment: environment object with fields and assign_group method
        group_ids: list of all valid group names
        step: current time step (unused in this simple strategy)
        """
        # Identify top-threat field (threat_level > 0)
        fields = getattr(environment, "fields", [])
        top_field = None
        top_threat = -1.0

        for field in fields:
            th = getattr(field, "threat_level", 0.0)
            if th > top_threat and th > 0.0:
                top_threat = th
                top_field = field

        # If no field needs protection, set all drones to idle (one pass)
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_field_id = top_field.id
        required = getattr(top_field, "drones_for_full_protection", 0)

        # Count how many drones are currently protecting the top field
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                current_protecting += 1

        # If already fully protected, keep those drones and set others idle (single pass)
        if current_protecting >= max(0, int(required)):
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                    environment.assign_group(d, f"protecting {top_field_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Need to allocate more drones
        needed = max(0, int(required) - current_protecting)

        # Build a single-pass assignment plan: determine for each drone its target group
        # We will assign exactly one group per drone.
        # First, mark drones that are already protecting the top field (keep them as is)
        # Then choose 'needed' drones from the rest to assign to protecting top_field_id
        # All others go to idle.
        # To satisfy "one assignment per drone", we determine the target_group per drone now.

        target_groups = ["idle"] * len(components)

        # Map index -> drone
        idx_to_drone = {i: d for i, d in enumerate(components)}

        # First pass: keep current protectors of top field
        for i, d in enumerate(components):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                target_groups[i] = f"protecting {top_field_id}"

        # If there are drones already protecting, don't count them again
        # Find candidates not already protecting top field
        candidates_indices = [i for i, d in enumerate(components) if target_groups[i] == "idle"]

        # If there are drones currently not protecting (idle or protecting other fields), we can consider them as candidates
        # Prefer idle drones among candidates (already aligned by initialization)
        # Allocate needed drones from candidates
        assigned = 0
        for idx in candidates_indices:
            if assigned >= needed:
                break
            # Reassign this drone to protect top field
            target_groups[idx] = f"protecting {top_field_id}"
            assigned += 1

        # Final pass: apply assignments in a single loop to ensure exactly one assignment per drone
        for i, d in enumerate(components):
            environment.assign_group(d, target_groups[i])