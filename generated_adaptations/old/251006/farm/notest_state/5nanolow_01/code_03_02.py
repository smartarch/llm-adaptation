import math

from generated_adaptations.base_classes.farm import FarmAdaptation as _BaseFarmAdaptation


class SmartFarmAdaptation(_BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance_point(self, p, qx, qy):
        dx = p.x - qx
        dy = p.y - qy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: reset all drones to idle (one assignment per drone)
        for d in components:
            environment.assign_group(d, "idle")

        # Step 2: identify fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            return  # nothing to protect

        # Step 3: pick the highest-threat field
        target_field = max(fields, key=lambda f: getattr(f, "threat_level", 0))

        # Step 4: determine how many drones are needed for full protection
        needed = int(getattr(target_field, "drones_for_full_protection", 1))
        if needed <= 0:
            return

        # Step 5: compute distance of each drone to the target field center
        cx, cy = self._field_center(target_field)
        drones_with_dist = []
        for d in components:
            dist = self._distance_point(d.location, cx, cy) if d.location is not None else float("inf")
            drones_with_dist.append((dist, d))

        # Step 6: sort by distance and pick the closest ones
        drones_with_dist.sort(key=lambda t: t[0])
        allocated = 0
        for dist, d in drones_with_dist:
            if allocated >= needed:
                break
            environment.assign_group(d, f"protecting {target_field.id}")
            allocated += 1

        # Remaining drones stay idle (already assigned to idle above)
        return