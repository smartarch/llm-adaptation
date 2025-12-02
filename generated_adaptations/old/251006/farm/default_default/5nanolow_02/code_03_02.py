import abc
import math

# The following import path is assumed by the prompt environment.
# It provides the base class that our adaptation must extend.
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved adaptation strategy (robust single-pass assignment):
    - Identify the field with the highest threat level (> 0).
    - Aim to fully protect that field by assigning exactly
      drones_for_full_protection drones to the group "protecting <field_id>".
    - Drones already protecting the top field stay in that group.
    - Prefer drones that are closest to the top field to minimize travel time.
    - All other drones are assigned to idle.
    - If there are no threatening fields, all drones are idle.
    - Ensure every drone is assigned exactly once per call.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Find the field with the highest threat level (> 0)
        top_field = None
        top_threat = 0.0

        for field in environment.fields:
            t = getattr(field, "threat_level", 0.0)
            if t > top_threat:
                top_threat = float(t)
                top_field = field

        # If no threatening field, idle all drones
        if top_field is None or top_threat <= 0.0:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Step 2: Determine how many drones are needed for full protection
        required_for_full = 1
        if hasattr(top_field, "drones_for_full_protection"):
            try:
                required_for_full = int(top_field.drones_for_full_protection)
            except Exception:
                required_for_full = 1

        top_group_name = f"protecting {top_field.id}"

        # Step 3: Build a list of drones with their distance to the top field center
        center_x, center_y = self._field_center(top_field)
        currently_protecting = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                currently_protecting.append(d)

        assigned = set()
        # Assign already protecting drones to the top group
        for d in currently_protecting:
            environment.assign_group(d, top_group_name)
            assigned.add(id(d))

        # Build a pool of remaining drones with distance to field center
        candidates = []
        for d in components:
            if id(d) in assigned:
                continue
            dist = 0.0
            if hasattr(d, "location") and d.location is not None:
                dist = math.hypot(d.location.x - center_x, d.location.y - center_y)
            candidates.append((dist, d))

        # Step 4: Sort by distance (closest first)
        candidates.sort(key=lambda t: t[0])

        # Step 5: Assign drones to top field until we reach the required amount
        needed = max(0, int(required_for_full) - len(currently_protecting))
        for dist, drone in candidates:
            if needed <= 0:
                break
            environment.assign_group(drone, top_group_name)
            assigned.add(id(drone))
            needed -= 1

        # Step 6: All remaining drones idle
        for dist, drone in candidates:
            if id(drone) in assigned:
                continue
            environment.assign_group(drone, "idle")