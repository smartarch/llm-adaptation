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
        # 1) Identify top-threat field (threat_level > 0)
        fields = getattr(environment, "fields", [])
        top_field = None
        top_threat = -1.0

        for field in fields:
            # Some environments may expose threat_level as a float in [0,1]
            th = getattr(field, "threat_level", 0.0)
            if th > top_threat and th > 0.0:
                top_threat = th
                top_field = field

        # If no field needs protection, set all drones to idle
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_field_id = top_field.id
        # 2) Determine current protection for the top field
        required = getattr(top_field, "drones_for_full_protection", 0)
        current_protecting = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                current_protecting += 1

        # If already fully protected, keep them there and set others to idle
        if current_protecting >= max(0, required):
            # Reassign all drones not currently protecting top field to idle
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                    # keep in the same group
                    environment.assign_group(d, f"protecting {top_field_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # 3) Compute how many more drones are needed
        needed = max(0, int(required) - current_protecting)
        if needed <= 0:
            # Nothing to allocate; ensure correct grouping for already protected drones
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                    environment.assign_group(d, f"protecting {top_field_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # 4) Gather candidate drones not already protecting the top field
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                # Already protecting top field; keep in place
                continue
            # If not protecting top field, consider as candidate
            candidates.append(d)

        # Sort candidates by a simple heuristic: prefer idle first (best to avoid churn)
        candidates.sort(key=lambda x: 0 if getattr(x, "state", None) == "idle" else 1)

        # 5) Assign needed drones to top field
        assigned = 0
        for cand in candidates:
            if assigned >= needed:
                break
            environment.assign_group(cand, f"protecting {top_field_id}")
            assigned += 1

        # 6) Set any remaining drones to idle
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id:
                # keep protecting if they were assigned to top field and needed amount satisfied
                if assigned > 0:
                    # They are already assigned to top field; ensure correct group
                    environment.assign_group(d, f"protecting {top_field_id}")
                    continue
            # If drone is not protecting top field, or there are still unassigned drones
            if getattr(d, "state", None) != "protecting" or getattr(d, "target_id", None) != top_field_id:
                environment.assign_group(d, "idle")