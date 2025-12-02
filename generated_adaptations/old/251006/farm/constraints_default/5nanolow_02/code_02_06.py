# One-pass allocation focused on the single most threatened field.
# - Identify the field with the highest threat (>0).
# - Allow drones protecting other fields to be reallocated if needed to fully protect the top field.
# - Drones already protecting the top field stay in place.
# - Remaining drones are assigned to protect the top field until its full_protection requirement is met.
# - Any leftover drones become idle.

from typing import List

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # 1) Find the most threatened field (threat_level > 0)
        best_field = None
        best_threat = -1.0
        for f in environment.fields:
            t = float(getattr(f, "threat_level", 0.0))
            if t > best_threat and t > 0.0:
                best_threat = t
                best_field = f

        if best_field is None:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        field_id = best_field.id
        # 2) Count how many drones are currently protecting the best field
        current_protecting = sum(
            1 for c in components
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id
        )

        # 3) How many drones are required for full protection of the best field
        required = getattr(best_field, "drones_for_full_protection", 0)
        try:
            required = int(required)
        except Exception:
            required = 0

        needed = max(0, required - current_protecting)

        # 4) Assign drones in a single pass:
        # - Keep drones already protecting the best field in that group
        # - Reallocate other drones to protect the best field until it is full
        # - Any remaining drones idle
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id:
                environment.assign_group(c, f"protecting {field_id}")
            elif needed > 0:
                environment.assign_group(c, f"protecting {field_id}")
                needed -= 1
            else:
                environment.assign_group(c, "idle")