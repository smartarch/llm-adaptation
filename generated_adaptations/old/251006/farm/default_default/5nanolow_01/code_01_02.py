import abc
import math

# Assuming the base class and necessary interfaces are importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into:
        - "idle": drones not protecting any field
        - "protecting {field.id}": drones protecting a specific field

        Strategy:
        - Consider fields with threat_level > 0 in descending order of threat.
        - For each field, if there are enough available drones to reach
          field.drones_for_full_protection, assign the closest drones to that field's center.
        - If not enough drones remain for a field, skip to the next field (to try for full protection elsewhere).
        - All remaining drones become idle.
        """
        # Prepare a mapping of field centers and sort fields by threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # Compute centers
        field_info = []
        for f in fields:
            left = getattr(f, "left", 0)
            top = getattr(f, "top", 0)
            right = getattr(f, "right", 0)
            bottom = getattr(f, "bottom", 0)
            center_x = (left + right) / 2.0
            center_y = (top + bottom) / 2.0
            needed = getattr(f, "drones_for_full_protection", 0)
            threat = getattr(f, "threat_level", 0)
            field_info.append((f, threat, needed, center_x, center_y))

        # Sort by threat level descending
        field_info.sort(key=lambda t: t[1], reverse=True)

        # Track which drones have been assigned to protecting groups
        assigned = set()

        # Helper to compute distance
        def dist(a, b):
            dx = a.location.x - b[0]
            dy = a.location.y - b[1]
            return dx * dx + dy * dy  # squared distance; enough for ordering

        # We need a pool of drones to choose from: all components
        # Build a list of (drone, index) for consistent ordering
        drones = list(components)
        # We'll maintain a set for quick membership
        remaining_indices = set(range(len(drones)))

        # For each field in priority order, attempt full protection if enough drones remain
        for f, threat, needed, cx, cy in field_info:
            if threat <= 0:
                continue
            if len(remaining_indices) < needed:
                # Not enough to fully protect this field; skip it for now
                continue

            # Choose the 'needed' closest drones to this field center
            # Build a list of (distance, index) for remaining drones
            dist_list = []
            for idx in remaining_indices:
                d = drones[idx]
                dx = d.location.x - cx
                dy = d.location.y - cy
                d2 = dx * dx + dy * dy
                dist_list.append((d2, idx))

            dist_list.sort(key=lambda t: t[0])
            chosen_indices = [idx for (_, idx) in dist_list[:needed]]

            # Assign these drones to the protecting group for this field
            group_name = f"protecting {f.id}"
            for idx in chosen_indices:
                environment.assign_group(drones[idx], group_name)
                assigned.add(idx)

            # Remove from remaining pool
            remaining_indices.difference_update(chosen_indices)

        # Finally, assign all drones not yet assigned to any protecting group to idle
        # Determine all drones that have not been assigned to a protecting group yet
        for idx, drone in enumerate(drones):
            if idx in assigned:
                continue
            environment.assign_group(drone, "idle")