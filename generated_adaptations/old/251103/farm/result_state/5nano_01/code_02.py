from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No field needs protection; idle all drones
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Helper to compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Choose the field with the highest threat level.
        # Tie-break by closest distance from any drone to the field center.
        best_field = None
        best_threat = -1.0
        best_dist = float("inf")

        for f in fields:
            cx, cy = center_of(f)
            # Distance to the nearest drone
            min_dist_to_field = float("inf")
            for d in components:
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < min_dist_to_field:
                    min_dist_to_field = dist

            if (f.threat_level > best_threat) or (
                abs(f.threat_level - best_threat) < 1e-9 and min_dist_to_field < best_dist
            ):
                best_field = f
                best_threat = f.threat_level
                best_dist = min_dist_to_field

        field = best_field
        group_name = f"protecting {field.id}"

        # Validate the group exists in the provided group_ids
        if group_name not in group_ids:
            # Fallback: idle all drones if the group is not available
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        required = getattr(field, "drones_for_full_protection", 0)

        # Drones currently protecting this field (based on drone state/target)
        current_protecting_indices = []
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == field.id:
                current_protecting_indices.append(idx)

        assigned_indices = set(current_protecting_indices)

        # Ensure current protecting drones stay in the correct protecting group
        for idx in current_protecting_indices:
            environment.assign_group(components[idx], group_name)

        # Build list of available candidates to fill the protection gap
        cx, cy = center_of(field)
        candidates = []
        for idx, d in enumerate(components):
            if idx in assigned_indices:
                continue
            dx = d.location.x - cx
            dy = d.location.y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            candidates.append((dist, idx))

        candidates.sort()  # closest first

        needed = max(0, int(required) - len(current_protecting_indices))
        for i in range(min(needed, len(candidates))):
            idx = candidates[i][1]
            environment.assign_group(components[idx], group_name)
            assigned_indices.add(idx)

        # Remaining drones idle
        for idx, d in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(d, "idle")