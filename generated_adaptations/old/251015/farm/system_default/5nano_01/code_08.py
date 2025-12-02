"""
Strategy reasoning and adaptation plan:

Goal:
- Minimize field damage by intelligently allocating drones to protect fields.
- Improve upon previous approaches by prioritizing protection not only by threat level but also by proximity; i.e., we assign the closest available drones to each target field to minimize travel time to protection.

Key ideas:
- Gather all fields with threat_level > 0 and sort them by threat descending.
- For each field in that order, try to allocate drones to fully protect the field using its drones_for_full_protection quota.
- When selecting drones for a field, pick the closest available drones (based on current drone location and the field center).
- If there aren’t enough drones to fully protect the next field, allocate all remaining drones to partially protect that field.
- After processing all threatening fields, any drones not allocated will be assigned to idle.
- Always re-assign each drone to a group each step (explicit re-assignment), and use the group name "protecting {field_id}" for protection.

This approach aims to maximize protection for the most threatening fields while minimizing the time-to-protection by using proximity-based drone selection.

"""

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Distribute drones to protect fields by:
          1) Sorting fields by threat (desc) and trying to fully protect each in order.
          2) Selecting closest available drones to each field when assigning for protection.
          3) If not enough drones remain to fully protect a field, assign all remaining to partially protect that field.
          4) Remaining drones go to idle.
        """
        # Gather fields with positive threat
        threatening_fields = []
        for f in getattr(environment, "fields", []) or []:
            threat = getattr(f, "threat_level", 0.0)
            try:
                threat_val = float(threat)
            except Exception:
                threat_val = 0.0
            if threat_val > 0.0:
                # Pre-compute field center for distance calculations
                left = getattr(f, "left", 0.0)
                top = getattr(f, "top", 0.0)
                right = getattr(f, "right", 0.0)
                bottom = getattr(f, "bottom", 0.0)
                cx = (left + right) / 2.0
                cy = (top + bottom) / 2.0
                threatening_fields.append((threat_val, f, cx, cy))

        # If no threatening fields, idle all drones
        if not threatening_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat descending
        threatening_fields.sort(key=lambda t: t[0], reverse=True)

        total_drones = len(components)
        assigned_indices = set()  # indices of drones already assigned to some field

        # Helper to compute distance from a drone to a field center
        def distance_to_field(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return math.hypot(dx, dy)

        remaining = total_drones

        # Process fields in order of threat, assigning closest drones first
        for threat_val, field, cx, cy in threatening_fields:
            if remaining <= 0:
                break
            field_id = getattr(field, "id", None)
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Build list of candidate drones not yet assigned, with distance to this field
            candidates = []
            for idx, drone in enumerate(components):
                if idx in assigned_indices:
                    continue
                dist = distance_to_field(drone, cx, cy)
                candidates.append((dist, idx, drone))

            # Sort by distance (closest first)
            candidates.sort(key=lambda t: t[0])

            if remaining >= required:
                take = required
            else:
                take = remaining  # partial protection with all remaining drones

            if take <= 0:
                continue

            # Assign the closest 'take' drones to protect this field
            for i in range(take):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {field_id}")
                assigned_indices.add(idx)
            remaining -= take

        # Any drones not assigned yet go idle
        for idx, drone in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(drone, "idle")