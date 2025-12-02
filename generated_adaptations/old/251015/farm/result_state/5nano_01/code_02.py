"""
Adaptation strategy rationale (embedded as comments in the code for clarity):

Task recap:
- We manage a fleet of drones to protect fields from birds.
- Fields have a threat_level and a target drones_for_full_protection.
- Drones can be idle or protecting a field (grouped as "protecting {field_id}").
- When protecting a field, we should allocate enough drones to reach full protection.
- The field with the highest threat level should be fully protected first using the closest drones.
- If that field is already fully protected, we keep its protecting drones as is and other drones can be idle or assigned elsewhere.

High-level strategy:
1) Identify all fields with threat_level > 0. If none, put all drones in "idle".
2) Pick the top field to protect: the one with the highest threat_level. If there is a tie, prefer the field where the closest available drones are, to honor "closest drones".
3) Determine how many drones are currently protecting that field (consider drones already en route or protecting to that field).
   - If current_protectors >= drones_for_full_protection, keep those drones in "protecting {field_id}" and assign all others to "idle".
   - If not fully protected, calculate shortfall = drones_for_full_protection - current_protectors.
     - Reassign all current protectors (en route or protecting) to the group "protecting {field_id}".
     - From the remaining drones, pick the closest ones to the field center to fill the shortfall, reassign them to the same group.
     - Any drones not assigned to this top field go to "idle".
4) Always ensure the group names exist in group_ids; otherwise fall back to all idle.

Notes:
- We consider both protecting and moving_to_field states as already contributing to protection (they are en route to the field).
- Distances are computed to the field center (center of left, right, top, bottom).

This implementation assigns groups deterministically per step, focusing on fully protecting the highest-threat field with the closest drones, and leaves others idle unless they are already protecting the top field.

"""

import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect candidate fields with threat
        candidates = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not candidates:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Pick the top field by threat_level
        top_field = max(candidates, key=lambda fld: getattr(fld, "threat_level", 0))

        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If the required group doesn't exist, default to idle
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Field center for distance calculations
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        def distance_to_field_center(dron):
            loc = getattr(dron, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - center_x
            dy = getattr(loc, "y", 0.0) - center_y
            return math.hypot(dx, dy)

        # 3) Determine current protectors for the top field
        current_protectors = []
        for d in components:
            state = getattr(d, "state", None)
            target = getattr(d, "target_id", None)
            if target == top_field.id and state in ("protecting", "moving_to_field"):
                current_protectors.append(d)

        # If the top field is already fully protected, keep current protectors there.
        # and idle all others (subject to maintaining continuity requirement by explicit re-assignments).
        drones_for_full = getattr(top_field, "drones_for_full_protection", 0)
        current_count = len(current_protectors)

        assigned = set()

        if current_count >= drones_for_full:
            # Fully protected: ensure current protectors are in the top group
            for d in current_protectors:
                environment.assign_group(d, top_group)
                assigned.add(d)
            # Remaining drones go idle
            for d in components:
                if d not in assigned:
                    environment.assign_group(d, "idle")
            return

        # Need to fill shortfall
        shortfall = max(0, drones_for_full - current_count)

        # Re-assign current protectors to top_group (they are already en route or protecting)
        for d in current_protectors:
            environment.assign_group(d, top_group)
            assigned.add(d)

        # Choose closest additional drones to fill the shortfall
        if shortfall > 0:
            # Exclude already assigned (current_protectors)
            candidates_for_extra = [d for d in components if d not in assigned]
            # Sort by distance to field center
            candidates_for_extra.sort(key=distance_to_field_center)
            for i in range(min(shortfall, len(candidates_for_extra))):
                d = candidates_for_extra[i]
                environment.assign_group(d, top_group)
                assigned.add(d)

        # All remaining drones idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")