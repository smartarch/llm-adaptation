from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, 'threat_level', 0.0) > 0.0]

        # If no threatening fields, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level descending
        fields_with_threat.sort(key=lambda f: getattr(f, 'threat_level', 0.0), reverse=True)

        # Helper to compute field center
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Prepare a fresh assignment map: drone -> target_group (string)
        assignment_map = {d: None for d in components}
        assigned_set = set()

        # Step 1: Top field protection
        top_field = fields_with_threat[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If group not available, fallback to idle
            top_group = "idle"

        drones_needed = getattr(top_field, "drones_for_full_protection", len(components))
        if drones_needed <= 0:
            drones_needed = len(components)

        # Current protectors for top field (based on actual drones that are already protecting it)
        current_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]

        for d in current_top:
            assignment_map[d] = top_group
            assigned_set.add(d)

        # If not enough, pick closest from unassigned drones
        if len(current_top) < drones_needed:
            cx, cy = center(top_field)
            candidates = []
            for d in components:
                if d in assigned_set:
                    continue
                loc = getattr(d, "location", None)
                dist = float('inf')
                if loc is not None:
                    dist = math.hypot(getattr(loc, "x", 0.0) - cx, getattr(loc, "y", 0.0) - cy)
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])
            needed = drones_needed - len(current_top)
            for i in range(min(needed, len(candidates))):
                d = candidates[i][1]
                assignment_map[d] = top_group
                assigned_set.add(d)

        # Step 2: Allocate remaining fields (in threat order) using drones not already assigned
        for f in fields_with_threat[1:]:
            group = f"protecting {f.id}"
            if group not in group_ids:
                continue

            # Current protectors for this field (if any were pre-assigned in this step)
            current_f = [
                d for d in components
                if assignment_map.get(d) == group
            ]
            needed_f = getattr(f, "drones_for_full_protection", len(components))
            if len(current_f) >= needed_f:
                # Already fully protected; keep them assigned to this group
                for d in current_f:
                    assigned_set.add(d)
                continue

            # Compute how many more are needed
            remaining_needed = max(0, needed_f - len(current_f))

            # Build candidate pool from drones not yet assigned to any group
            cx, cy = center(f)
            candidates = []
            for d in components:
                if d in assigned_set:
                    continue
                loc = getattr(d, "location", None)
                dist = float('inf')
                if loc is not None:
                    dist = math.hypot(getattr(loc, "x", 0.0) - cx, getattr(loc, "y", 0.0) - cy)
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            # Assign the closest drones to this field
            selected = list(current_f)
            for i in range(min(remaining_needed, len(candidates))):
                d = candidates[i][1]
                selected.append(d)

            for d in selected:
                assignment_map[d] = group
                assigned_set.add(d)

        # Step 3: Default any unassigned drones to idle
        for d in components:
            if assignment_map[d] is None:
                assignment_map[d] = "idle"

        # Finally, apply all assignments in a single pass (exactly one assignment per drone)
        for d, grp in assignment_map.items():
            environment.assign_group(d, grp)