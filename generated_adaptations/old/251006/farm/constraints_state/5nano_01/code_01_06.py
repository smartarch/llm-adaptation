"""
Adaptation strategy (updated):
- Gather all fields with positive threat level and sort them by threat descending.
- For each such field, if there is a corresponding "protecting {field_id}" group, allocate drones to protect it
  until the field reaches its required drones_for_full_protection. Always ensure drones currently protecting the field remain in that
  group's protection.
- Drones are chosen from those not yet assigned to any protection group, preferring the closest drones to the field's center.
- If a field's protection group is not available, skip it and leave drones idle for that step.
- After evaluating all threatened fields, apply exactly one environment.assign_group call per drone (no repeated assignments per step).
- If there are no threatened fields, put all drones to idle.
"""
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        threatened_fields = [
            f for f in environment.fields if getattr(f, "threat_level", 0) > 0
        ]

        if not threatened_fields:
            # No threats: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Prepare final mapping: drone -> group
        final_group = {d: "idle" for d in components}

        # Iterate fields in order of threat
        for field in threatened_fields:
            group = f"protecting {field.id}"
            # Only consider this field if the corresponding group exists
            if group not in group_ids:
                continue

            # Drones currently protecting this field should stay in this group
            current_protectors = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            for d in current_protectors:
                final_group[d] = group

            current_count = len(current_protectors)
            needed = max(0, int(getattr(field, "drones_for_full_protection", 0)) - current_count)
            if needed <= 0:
                continue

            # Field center for distance calculations
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            # Candidates: drones not yet assigned to protection groups
            candidates = []
            for d in components:
                if final_group[d] != "idle":
                    continue
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            # Assign the closest drones needed to this field
            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group[drone] = group

        # Apply assignments: exactly one call per drone
        for d in components:
            environment.assign_group(d, final_group[d])