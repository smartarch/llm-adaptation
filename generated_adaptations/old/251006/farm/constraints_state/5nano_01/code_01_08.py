"""
Adaptation strategy (robust, single-pass assignments):
- Determine threatened fields ( threat_level > 0 ) and sort by threat descending.
- Always try to fully protect the most threatened field first (top field) using the closest drones.
  - Current drones already protecting that field stay in that field's group.
  - To fill the top field, consider all drones that are not currently protecting the top field and assign the closest ones to "protecting {top_field.id}".
- After securing the top field, allocate drones to the remaining threatened fields (in threat order) only from drones that are still idle
  (to avoid moving drones that were already allocated to higher-threat fields).
- If a field's protection group is not available in group_ids, skip it.
- If there are no threatened fields, assign all drones to idle.
- Ensure exactly one environment.assign_group call per drone per step.
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
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Final mapping: start with all idle
        final_group = {d: "idle" for d in components}

        # Phase 1: Fully protect the top-threat field
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group in group_ids:
            # Current protectors for the top field
            current_top = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
            ]
            for d in current_top:
                final_group[d] = top_group

            current_count = len(current_top)
            needed = max(0, int(getattr(top_field, "drones_for_full_protection", 0)) - current_count)

            if needed > 0:
                cx = (top_field.left + top_field.right) / 2.0
                cy = (top_field.top + top_field.bottom) / 2.0

                # Candidates: any drone not currently protecting the top field
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

        # Phase 2: Allocate remaining drones to other threatened fields (after top) using idle drones only
        for field in threatened_fields[1:]:
            group = f"protecting {field.id}"
            if group not in group_ids:
                continue

            current = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            current_count = len(current)
            max_required = int(getattr(field, "drones_for_full_protection", 0))
            needed = max(0, max_required - current_count)
            if needed <= 0:
                continue

            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0

            candidates = []
            current_set = set(current)
            for d in components:
                if d in current_set:
                    continue  # skip drones already protecting this field
                if final_group[d] != "idle":
                    continue  # only idle drones should be considered for secondary fields
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                candidates.append((dist, d))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group[drone] = group

        # Phase 3: Assign remaining drones to idle
        for d in components:
            environment.assign_group(d, final_group[d])