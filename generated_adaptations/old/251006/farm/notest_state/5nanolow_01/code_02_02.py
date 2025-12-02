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
        # Step 1: reset all drones to idle
        for d in components:
            environment.assign_group(d, "idle")

        # Step 2: identify fields with threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threat: keep all idle
            return

        # Step 3: compute current protection (based on observed states, but we will reassign anyway)
        field_for_protection = None
        # Pick the highest threat field that is not fully protected
        fields_sorted = sorted(fields, key=lambda x: x.threat_level, reverse=True)
        for f in fields_sorted:
            max_needed = getattr(f, "drones_for_full_protection", 1)
            # Count drones currently assigned to protect this field (state within environment may be stale since we reset)
            # To be robust, we approximate by assuming 0 since we reset. We'll still attempt to fill using closest drones.
            current = 0  # after reset it's zero
            if current < max_needed:
                field_for_protection = f
                break

        if field_for_protection is None:
            return

        # Step 4: allocate the closest drones to protect the target field
        cx, cy = self._field_center(field_for_protection)

        # List all drones with their distance to field center
        drones_with_dist = []
        for d in components:
            dist = 0.0
            if d.location is not None:
                dist = self._distance_point(d.location, cx, cy)
            else:
                dist = float("inf")
            drones_with_dist.append((dist, d))

        drones_with_dist.sort(key=lambda t: t[0])

        needed = max(0, int(getattr(field_for_protection, "drones_for_full_protection", 1)) - 0)

        allocated = 0
        for dist, d in drones_with_dist:
            if allocated >= needed:
                break
            # Assign this drone to protect the target field
            environment.assign_group(d, f"protecting {field_for_protection.id}")
            allocated += 1

        # Any remaining drones stay idle (already assigned to idle above)
        return