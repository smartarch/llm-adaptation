# Strategy reasoning (embedded as comments for clarity)
# - We assign exactly one group to every drone in a single pass.
# - Drones currently protecting a field keep protecting that field (group stays "protecting <field_id>").
# - Other drones are allocated to protect fields in order of decreasing threat until each field
#   reaches its required full-protection drone count. If there are no more drones needed for the
#   top fields, remaining drones become idle.
# - This guarantees:
#   1) No drone is assigned to multiple groups in one call.
#   2) The most threatened fields get full protection first.

from typing import List

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Collect fields with positive threat and sort by threat descending
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        fields_with_threat.sort(key=lambda f: float(getattr(f, "threat_level", 0.0)), reverse=True)

        # If no field needs protection, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper to count drones currently protecting a given field
        def currently_protecting(field_id: str) -> int:
            return sum(
                1 for c in components
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id
            )

        # Determine desired group for each drone (one assignment per drone)
        desired_groups = [None] * len(components)

        # First, keep drones already protecting in their current protection group
        for idx, c in enumerate(components):
            if getattr(c, "state", None) == "protecting":
                field_id = getattr(c, "target_id", None)
                if field_id is not None:
                    desired_groups[idx] = f"protecting {field_id}"
                else:
                    desired_groups[idx] = "idle"

        # Build a list of drones that are not yet assigned to a protecting group
        unassigned_indices = [i for i, g in enumerate(desired_groups) if g is None]

        # Allocate unassigned drones to fields in threat order until full protection is reached
        for field in fields_with_threat:
            field_id = field.id
            current = currently_protecting(field_id)
            required = getattr(field, "drones_for_full_protection", 0)
            try:
                required = int(required)
            except Exception:
                required = 0

            needed = max(0, required - current)
            while needed > 0 and unassigned_indices:
                idx = unassigned_indices.pop(0)
                desired_groups[idx] = f"protecting {field_id}"
                needed -= 1

        # Any remaining drones (still None) become idle
        for i, g in enumerate(desired_groups):
            if g is None:
                desired_groups[i] = "idle"

        # Apply assignments (one per drone)
        for c, grp in zip(components, desired_groups):
            environment.assign_group(c, grp)