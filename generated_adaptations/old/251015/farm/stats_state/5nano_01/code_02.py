import math
import abc

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, p, q):
        dx = getattr(p, 'x', 0.0) - getattr(q, 0.0)
        dy = getattr(p, 'y', 0.0) - getattr(q, 1.0)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields_with_threat = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Sort fields by threat level (desc)
        fields_with_threat.sort(key=lambda f: getattr(f, 'threat_level', 0), reverse=True)
        top_field = fields_with_threat[0]
        top_group = f"protecting {top_field.id}"

        # Helper to count current protecting drones for a given field
        def current_protecting_for(field):
            return [d for d in components if getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) == field.id]

        assigned_drones = set()

        # Step 1: Keep drones currently protecting top_field in the top_group
        top_current = current_protecting_for(top_field)
        for d in top_current:
            environment.assign_group(d, top_group)
            assigned_drones.add(d)

        # Step 2: If top_field not fully protected, assign nearest drones to reach full protection
        top_needed = max(0, getattr(top_field, 'drones_for_full_protection', 0) - len(top_current))
        if top_needed > 0:
            # Compute center and distances for all drones not yet assigned to top_group
            center_top = self._field_center(top_field)
            candidates = []
            for d in components:
                if d in assigned_drones:
                    continue
                dist = math.hypot(getattr(d.location, 'x', 0.0) - center_top[0],
                                  getattr(d.location, 'y', 0.0) - center_top[1])
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])
            for i in range(min(top_needed, len(candidates))):
                drone = candidates[i][1]
                environment.assign_group(drone, top_group)
                assigned_drones.add(drone)

        # Step 3: Handle other fields (besides top_field) in threat order
        for f in fields_with_threat[1:]:
            group = f"protecting {f.id}"
            current = current_protecting_for(f)
            current_count = len(current)

            if current_count >= getattr(f, 'drones_for_full_protection', 0):
                # Field already fully protected; ensure current drones stay in this group
                for d in current:
                    environment.assign_group(d, group)
                continue

            needed = max(0, getattr(f, 'drones_for_full_protection', 0) - current_count)
            if needed <= 0:
                continue

            # Build pool of available drones (not already assigned)
            center_f = self._field_center(f)
            pool = []
            for d in components:
                if d in assigned_drones:
                    continue
                dist = math.hypot(getattr(d.location, 'x', 0.0) - center_f[0],
                                  getattr(d.location, 'y', 0.0) - center_f[1])
                pool.append((dist, d))
            pool.sort(key=lambda t: t[0])

            for i in range(min(needed, len(pool))):
                drone = pool[i][1]
                environment.assign_group(drone, group)
                assigned_drones.add(drone)

        # Step 4: Idle all remaining drones
        for d in components:
            if d not in assigned_drones:
                environment.assign_group(d, "idle")