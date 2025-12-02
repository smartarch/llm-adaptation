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

        # One-pass plan: determine target group for each drone
        target_groups = ["idle"] * len(components)

        # First, preserve current protectors of top field
        for i, d in enumerate(components):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                target_groups[i] = f"protecting {top_field_id}"

        # Prepare list of idle indices (drones that are idle now)
        idle_indices = [i for i, d in enumerate(components) if getattr(d, "state", None) == "idle"]

        # Allocate as many needed drones from idle pool
        assigned = 0
        for idx in idle_indices:
            if assigned >= needed:
                break
            target_groups[idx] = f"protecting {top_field_id}"
            assigned += 1

        # Remaining drones stay idle (or remain in their current protect state if already assigned above)
        for i in range(len(components)):
            environment.assign_group(components[i], target_groups[i])