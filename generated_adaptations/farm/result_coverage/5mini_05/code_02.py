from typing import List
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Strategy:
        - Identify the field with the highest threat_level (>0).
        - Count drones already committed to that field (target_id == field.id and state in {'protecting','moving_to_field'}).
        - If more drones are needed, pick the closest drones (by Euclidean distance to field center) among the remaining drones.
        - Assign all chosen drones to "protecting {field.id}" and all others to "idle".
        - Always call environment.assign_group for every component.
        """

        # Helper: compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: Euclidean distance between drone and (x,y)
        def distance(drone, x, y):
            dx = drone.location.x - x
            dy = drone.location.y - y
            return math.hypot(dx, dy)

        # Ensure group name presence
        idle_group = "idle"

        # Find threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all to idle
        if not threatened_fields:
            for comp in components:
                grp = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)
                environment.assign_group(comp, grp)
            return

        # Select the field with highest threat_level (tie broken by id for determinism)
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, getattr(f, "id", "")))

        # Build the exact protecting group name and verify it's a valid group id
        protecting_group_name = f"protecting {target_field.id}"
        if protecting_group_name not in group_ids:
            # fallback: if the specific protecting group not available, assign all to idle
            for comp in components:
                grp = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)
                environment.assign_group(comp, grp)
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))

        cx, cy = field_center(target_field)

        # Identify currently committed drones to this field (either protecting or moving_to_field and target matches)
        committed = []
        not_committed = []
        for comp in components:
            if getattr(comp, "target_id", None) == target_field.id and getattr(comp, "state", "") in ("protecting", "moving_to_field"):
                committed.append(comp)
            else:
                not_committed.append(comp)

        committed_count = len(committed)
        needed = max(0, required - committed_count)

        # If more drones needed, pick the closest ones from not_committed
        selected_for_protection = set()
        # Always include already committed ones
        for c in committed:
            selected_for_protection.add(c)

        if needed > 0 and not_committed:
            # sort not_committed by distance to field center
            sorted_candidates = sorted(not_committed, key=lambda d: distance(d, cx, cy))
            for d in sorted_candidates[:needed]:
                selected_for_protection.add(d)

        # Now assign groups: chosen ones to protecting group, others to idle
        for comp in components:
            if comp in selected_for_protection:
                environment.assign_group(comp, protecting_group_name)
            else:
                grp = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)
                environment.assign_group(comp, grp)