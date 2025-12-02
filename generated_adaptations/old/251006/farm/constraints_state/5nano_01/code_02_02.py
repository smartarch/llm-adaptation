"""
Improved adaptation strategy (top-field-first, robust and test-friendly):
- Identify threatened fields (threat_level > 0) and pick the most threatened field.
- If a corresponding "protecting {field_id}" group exists, attempt to fully protect that field.
- Current protectors of the top field stay in the top group.
- Fill the remaining protection need by selecting the closest drones to the field center, regardless of their current assignments (they will be reassigned to the top field if needed).
- After ensuring the top field reaches its required drones, assign all other drones to idle (to avoid unintended movements and ensure exactly one assignment per drone).
- If the top field's protection group is not available, fall back to idle for all drones.
- This focuses on maximizing protection for the most dangerous field while keeping the assignment simple and compliant with unit tests (one group assignment per drone).
"""
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields
        threatened_fields = [
            f for f in environment.fields if getattr(f, "threat_level", 0) > 0
        ]

        if not threatened_fields:
            # No threats: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort by threat level (highest first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # If the top group's not valid, default to idle for all
        if top_group not in group_ids:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Build final assignment mapping (one call per drone)
        final_group = {d: "idle" for d in components}

        # Current protectors of the top field
        current_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        for d in current_top:
            final_group[d] = top_group

        current_count = len(current_top)
        needed = max(0, int(getattr(top_field, "drones_for_full_protection", 0)) - current_count)

        if needed > 0:
            # Center of the field for distance calculation
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Candidates: all drones not already in the top group
            candidates = []
            top_set = set(current_top)
            for d in components:
                if d in top_set:
                    continue
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group[drone] = top_group

        # Apply assignments: exactly once per drone
        for d in components:
            environment.assign_group(d, final_group[d])