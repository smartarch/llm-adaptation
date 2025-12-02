# Reasoning and adaptation strategy (embedded as comments in the code)
# - The goal is to allocate drones to protect fields, prioritizing the field with the
#   highest threat level. We should fully protect that field using the closest drones.
# - To reduce unnecessary churn (reassignments), we preserve drones that are already protecting
#   some field whenever possible. We only move drones to top/second fields when needed to
#   reach full protection.
# - If the top field becomes fully protected, we then consider the next highest-threat field and
#   allocate additional drones to it, again favoring drones that minimize movement.
# - All drones must be assigned to one of the allowed groups. Drones that are currently protecting
#   another field should keep their group identity when not being reassigned to top/second.
# - This approach aims to reduce idle drones when there are fields with positive threat and to limit
#   the frequency of reassignments (e.g., avoid moving a drone from Field_3 to Field_1 too often).

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0.0) > 0.0]

        # If there are no threats, put everyone to idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Determine the top (highest threat) field
        top_field = max(threatened_fields, key=lambda ff: getattr(ff, "threat_level", 0.0))
        top_group = f"protecting {top_field.id}"

        # Center coordinates of the top field
        cx_top = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
        cy_top = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0
        top_protectors = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id]
        need_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - len(top_protectors))

        # Step 1: Allocate drones to top field using closest available drones
        newly_assigned_top = []
        if need_top > 0:
            candidates = []
            for d in components:
                if d in top_protectors:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - cx_top
                    dy = getattr(loc, "y", 0.0) - cy_top
                    dist = (dx * dx + dy * dy) ** 0.5
                # Prefer idle drones first to minimize disruption
                is_idle = 1 if getattr(d, "state", "") == "idle" else 0
                candidates.append((is_idle, dist, d))
            candidates.sort(key=lambda t: (t[0], t[1]))
            take = min(need_top, len(candidates))
            for i in range(take):
                newly_assigned_top.append(candidates[i][2])

        # Step 2: Optionally allocate to the second-highest-threat field if top is covered
        second_field = None
        if len(threatened_fields) > 1:
            # Exclude top_field and pick the next highest threat
            others = [f for f in threatened_fields if f.id != top_field.id]
            if others:
                second_field = max(others, key=lambda ff: getattr(ff, "threat_level", 0.0))
        second_group = None
        second_protectors = []
        if second_field is not None:
            second_group = f"protecting {second_field.id}"
            second_protectors = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == second_field.id]
            need_second = max(0, getattr(second_field, "drones_for_full_protection", 0) - len(second_protectors))

            if need_second > 0:
                # Candidates exclude top_field drones and existing second_field protectors
                top_set = set(top_protectors)
                second_set = set(second_protectors)
                candidates2 = []
                center_second_x = (getattr(second_field, "left", 0) + getattr(second_field, "right", 0)) / 2.0
                center_second_y = (getattr(second_field, "top", 0) + getattr(second_field, "bottom", 0)) / 2.0
                for d in components:
                    if d in top_set or d in second_set:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - center_second_x
                        dy = getattr(loc, "y", 0.0) - center_second_y
                        dist = (dx * dx + dy * dy) ** 0.5
                    state = getattr(d, "state", "")
                    is_idle = 1 if state == "idle" else 0
                    candidates2.append((is_idle, dist, d))
                candidates2.sort(key=lambda t: (t[0], t[1]))
                take2 = min(need_second, len(candidates2))
                for i in range(take2):
                    d = candidates2[i][2]
                    environment.assign_group(d, second_group)

        # Step 3: Final per-drone assignment to minimize churn
        # Build sets for quick checks
        top_set_all = set(top_protectors)
        if newly_assigned_top:
            top_set_all.update(newly_assigned_top)
        second_set_all = set(second_protectors) if second_field is not None else set()

        for d in components:
            if d in top_set_all:
                environment.assign_group(d, top_group)
            elif d in second_set_all and second_field is not None:
                environment.assign_group(d, second_group)
            else:
                # Preserve continuity where possible:
                st = getattr(d, "state", "")
                tgt = getattr(d, "target_id", None)
                if st in ("protecting", "moving_to_field") and tgt is not None:
                    environment.assign_group(d, f"protecting {tgt}")
                else:
                    environment.assign_group(d, "idle")