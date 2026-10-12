import abc
from generated_adaptations.base_classes.farm import FarmAdaptation
from typing import List

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of previous assignments: drone -> group_id
        self._prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        n = len(drones)

        # If no drones, nothing to do
        if n == 0:
            return

        # Discover threatened fields (threat_level > 0), sorted by threat desc
        threatened_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Prepare field -> group mapping
        field_group_map = {}
        for f in threatened_fields:
            field_group_map[f.id] = f"protecting {f.id}"

        # Compute desired number of drones per field
        desired_by_field = {}
        min_protect = (n + 1) // 2  # at least half protecting

        if threatened_fields:
            top_field = threatened_fields[0]
            top_group = field_group_map[top_field.id]
            max_top = int(getattr(top_field, "drones_for_full_protection", 0))
            max_top = max(0, min(max_top, n))
            desired_by_field[top_field.id] = max_top
            remaining = n - max_top

            # Allocate to subsequent fields in threat order
            for f in threatened_fields[1:]:
                if remaining <= 0:
                    break
                max_for_field = int(getattr(f, "drones_for_full_protection", 0))
                take = min(max_for_field, remaining)
                if take > 0:
                    desired_by_field[f.id] = take
                    remaining -= take

            # If total desired < min_protect, boost protection up to limits to meet threshold
            total_desired = sum(desired_by_field.values()) if desired_by_field else 0
            if total_desired < min_protect:
                for f in threatened_fields:
                    if total_desired >= min_protect:
                        break
                    cur = desired_by_field.get(f.id, 0)
                    cap = int(getattr(f, "drones_for_full_protection", 0))
                    if cur < cap:
                        add = min(cap - cur, min_protect - total_desired)
                        if add > 0:
                            desired_by_field[f.id] = cur + add
                            total_desired += add

        # Compute centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        def dist_to_field(drone, field):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            x = getattr(loc, "x", 0.0)
            y = getattr(loc, "y", 0.0)
            cx, cy = field_centers.get(field.id, (0.0, 0.0))
            dx = x - cx
            dy = y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Build assignment plan: for each field, pick drones to protect it
        assigned_by_drone = {}
        assigned_set = set()

        # Helper: get a top field delta-sorted list of drones to consider
        if threatened_fields:
            top_field = threatened_fields[0]
            top_group = field_group_map[top_field.id]
            desired_top = desired_by_field.get(top_field.id, 0)

            # Sort drones by distance to top field, with a small bias to keep
            # drones that were protecting the top field previously
            def top_sort_key(d):
                d_to_top = dist_to_field(d, top_field)
                prev_top = (self._prev_assignments.get(d) == top_group)
                # Bias slightly in favor of drones that were already protecting the top field
                bias = -0.01 if prev_top else 0.0
                return (d_to_top + bias)

            if desired_top > 0:
                candidates = sorted(drones, key=top_sort_key)
                for d in candidates[:desired_top]:
                    assigned_by_drone[d] = top_group
                    assigned_set.add(d)

        # For the remaining fields (in threat order), allocate drones similarly
        if threatened_fields:
            for f in threatened_fields[1:]:
                if f.id not in desired_by_field:
                    continue
                need = int(desired_by_field[f.id])
                if need <= 0:
                    continue
                group_id = field_group_map[f.id]

                # Sort by distance to this field, with tie-breaker using previous assignment to that field
                def field_sort_key(d):
                    d_to_field = dist_to_field(d, f)
                    prev_here = (self._prev_assignments.get(d) == group_id)
                    return (d_to_field, -1 if prev_here else 0)

                # Pick drones not already assigned
                candidates = [d for d in drones if d not in assigned_set]
                candidates.sort(key=field_sort_key)

                for d in candidates[:need]:
                    assigned_by_drone[d] = group_id
                    assigned_set.add(d)

        # Any remaining drones go idle
        for d in drones:
            if d not in assigned_set:
                assigned_by_drone[d] = "idle"

        # Apply environment group assignments (explicitly re-assign even if same group)
        for d, grp in assigned_by_drone.items():
            environment.assign_group(d, grp)

        # Update memory of assignments
        new_memory = {}
        for d in drones:
            new_memory[d] = assigned_by_drone.get(d, "idle")
        self._prev_assignments = new_memory