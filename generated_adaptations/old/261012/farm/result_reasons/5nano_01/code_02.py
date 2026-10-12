from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist across calls to encourage stability
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Distribute drones among fields to fully protect the most threatened fields.
        - Always fully protect the field with the highest threat_level (> 0) if possible.
        - Use the closest available drones to that field.
        - Do not over-protect a field (respect drones_for_full_protection).
        - Maintain some persistence across steps to satisfy "stability" requirements.
        - Unassigned drones go to the 'idle' group.
        """
        N = len(components)
        if N == 0:
            return

        # Prepare field list with threat > 0
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            # No threat: all drones idle
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_assignments[components.index(c)] = "idle"
            return

        # Sort fields by threat level descending (most threatened first)
        fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute distance from drone to field center
        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return sqrt(dx * dx + dy * dy)

        # Track which drones we are assigning to which group
        assigned_group = {}

        used = set()  # indices of drones already allocated to some protecting group

        # First pass: allocate to top fields greedily (fully protect if possible)
        max_target_drones = int(N)  # upper bound for allocations

        for field in fields_sorted:
            target_group = f"protecting {field.id}"
            drones_for_this_field = int(getattr(field, "drones_for_full_protection", 0))

            # Number of drones we can still allocate to this field
            available_slots = max(0, drones_for_this_field - len([i for i in used if i in assigned_group and assigned_group[i] == target_group]))
            # If there is no existing allocation to this field, available_slots starts as drones_for_this_field
            available_slots = drones_for_this_field - len([idx for idx, g in assigned_group.items() if g == target_group])

            # Collect candidate drones not yet allocated
            candidates = [i for i in range(N) if i not in used]

            if not candidates:
                continue

            cx, cy = field_center(field)

            # Compute distance and priority (prefer drones previously protecting this field)
            def candidate_key(i):
                drone = components[i]
                dx = drone.location.x - cx
                dy = drone.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                prev_on_field = (self.prev_assignments.get(i) == target_group)
                # Prefer closer drones; if same distance, prefer drones that were already protecting this field
                return (dist, 0 if prev_on_field else 1)

            candidates.sort(key=candidate_key)

            # How many to take for this field
            take = min(available_slots, len(candidates))
            if take <= 0:
                continue

            for idx in range(take):
                i = candidates[idx]
                assigned_group[i] = target_group
                used.add(i)

        # Second pass: if top field isn't fully protected but we have drones left, allocate more to top field
        if fields_sorted:
            top_field = fields_sorted[0]
            top_group = f"protecting {top_field.id}"
            drones_needed = int(getattr(top_field, "drones_for_full_protection", 0))
            current_top_assigned = [i for i in range(N) if assigned_group.get(i) == top_group]
            remaining_slots = max(0, drones_needed - len(current_top_assigned))

            if remaining_slots > 0:
                # Get candidates not yet allocated
                candidates = [i for i in range(N) if i not in used]
                if candidates:
                    cx, cy = field_center(top_field)

                    def key_for_top(i):
                        drone = components[i]
                        dx = drone.location.x - cx
                        dy = drone.location.y - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                        prev_on_field = (self.prev_assignments.get(i) == top_group)
                        return (dist, 0 if prev_on_field else 1)

                    candidates.sort(key=key_for_top)

                    take = min(remaining_slots, len(candidates))
                    for idx in range(take):
                        i = candidates[idx]
                        assigned_group[i] = top_group
                        used.add(i)

        # Stabilization step: ensure at least 25% of drones stay on the top field
        k_stable = max(1, int(0.25 * N))
        if fields_sorted:
            top_field = fields_sorted[0]
            top_group = f"protecting {top_field.id}"
            current_top_assigned = [i for i in range(N) if assigned_group.get(i) == top_group]
            if len(current_top_assigned) < k_stable:
                # We try to bring back some drones that were previously protecting the top field
                candidates = [i for i in range(N)
                              if self.prev_assignments.get(i) == top_group and assigned_group.get(i) != top_group]
                # Sort by closeness to top field center to choose closest stabilizing drones
                cx, cy = field_center(top_field)
                def stabilizing_key(i):
                    drone = components[i]
                    dx = drone.location.x - cx
                    dy = drone.location.y - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                    return dist
                candidates.sort(key=stabilizing_key)

                for i in candidates:
                    if len([idx for idx in range(N) if assigned_group.get(idx) == top_group]) >= min(drones_needed, N) and (
                        len([idx for idx in range(N) if assigned_group.get(idx) == top_group]) >= k_stable
                    ):
                        break
                    # Reassign this drone to the top field
                    assigned_group[i] = top_group
                    self.prev_assignments[i] = top_group

        # Third, ensure we mark all drones not assigned to a protecting group as idle
        for idx in range(N):
            if idx in assigned_group:
                group = assigned_group[idx]
                # If somehow an invalid/empty group sneaks in, reset to idle
                if group is None or not isinstance(group, str) or group.strip() == "":
                    group = "idle"
                    assigned_group[idx] = group
                    self.prev_assignments[idx] = group
            else:
                assigned_group[idx] = "idle"
                # update memory
                self.prev_assignments[idx] = "idle"

        # Finally, apply groups to all drones
        for i, comp in enumerate(components):
            group_id = assigned_group.get(i, "idle")
            environment.assign_group(comp, group_id)
            # Update memory
            self.prev_assignments[i] = group_id