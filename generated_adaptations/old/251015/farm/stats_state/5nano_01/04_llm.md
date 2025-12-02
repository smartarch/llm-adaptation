"""
Reasoning and improved adaptation strategy (embedded as comments in the code):

Goal
- Minimize damage by allocating drones to protect fields from birds.
- Prioritize the most threatened field, ensure full protection, and minimize drone movement between steps.
- Keep drones already protecting a field if that field is already fully protected. Only move drones when needed to reach full protection for the top threat.

Key observations from the evaluation
- High average protection for the top field should be achieved with the minimum necessary drones, and drones already en route or nearby should be reused to avoid extra travel time.
- Reducing moves between fields lowers the "moving to field" overhead and speeds up protection response.
- If a field is already fully protected, keep those drones in place (do not relocate unless there is a higher-priority need).

Improved strategy
1) Identify all fields with threat_level > 0 and sort by threat (desc). Target the top field first (most threatened).
2) For the top field:
   - Compute current protecting drones for that field.
   - If not fully protected, keep drones already protecting it, then add the nearest available drones to reach full protection.
   - When selecting candidates, prefer drones already moving toward the top field (to minimize arrival time) and then nearest by distance to the field center.
3) Allocate drones to other threatened fields (in threat order) only after ensuring top field is fully protected. For each other field:
   - If not fully protected, assign the nearest available drones not already allocated to the top field or other fields unless necessary.
   - Again, prefer drones already moving toward that field to reduce travel time.
4) Any drones not allocated to protection groups are set to idle.
5) All distance calculations are done to the field centers to approximate travel time.

Notes
- We assign groups exactly as: "idle" and "protecting {field.id}" for each threatened field.
- If multiple fields have threat > 0, drones will be distributed to maximize protection, prioritizing the most threatened field first and then others only as needed.

Now the Python implementation follows.
"""

import math
import abc

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance_point(self, p_x, p_y, q_x, q_y):
        dx = p_x - q_x
        dy = p_y - q_y
        return math.hypot(dx, dy)

    def _dist_drone_to_field_center(self, drone, field):
        cx, cy = self._field_center(field)
        return self._distance_point(drone.location.x, drone.location.y, cx, cy)

    def _current_top_drones(self, top_field, components):
        return [d for d in components if getattr(d, 'state', '') == 'protecting'
                and getattr(d, 'target_id', None) == getattr(top_field, 'id', None)]

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields_with_threat = []
        for f in environment.fields:
            if getattr(f, 'threat_level', 0) > 0:
                fields_with_threat.append(f)

        # If no threat, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (desc)
        fields_with_threat.sort(key=lambda f: getattr(f, 'threat_level', 0), reverse=True)
        top_field = fields_with_threat[0]
        top_group = f"protecting {top_field.id}"

        assigned = set()

        # Step 1: Keep drones currently protecting top_field in the top_group
        top_current = self._current_top_drones(top_field, components)
        for d in top_current:
            environment.assign_group(d, top_group)
            assigned.add(d)

        # Step 2: If top_field not fully protected, assign nearest drones
        top_needed = max(0, getattr(top_field, 'drones_for_full_protection', 0) - len(top_current))
        if top_needed > 0:
            center_top_x, center_top_y = self._field_center(top_field)
            candidates = []
            for d in components:
                if d in assigned:
                    continue
                dist = math.hypot(d.location.x - center_top_x, d.location.y - center_top_y)
                # Prioritize drones already moving toward the top field
                weight = 0
                if getattr(d, 'state', '') == 'moving_to_field' and getattr(d, 'target_id', None) == top_field.id:
                    weight -= 50.0
                candidates.append((dist + weight, d))
            candidates.sort(key=lambda t: t[0])
            for i in range(min(top_needed, len(candidates))):
                drone = candidates[i][1]
                environment.assign_group(drone, top_group)
                assigned.add(drone)

        # Step 3: Handle other fields in threat order
        for f in fields_with_threat[1:]:
            group = f"protecting {f.id}"
            current = [d for d in components if getattr(d, 'state', '') == 'protecting'
                       and getattr(d, 'target_id', None) == f.id]
            current_count = len(current)

            if current_count >= getattr(f, 'drones_for_full_protection', 0):
                # Field already fully protected; ensure they remain in this group
                for d in current:
                    environment.assign_group(d, group)
                continue

            needed = max(0, getattr(f, 'drones_for_full_protection', 0) - current_count)
            if needed <= 0:
                continue

            center_fx, center_fy = self._field_center(f)
            pool = []
            for d in components:
                if d in assigned or d in current:
                    continue
                dist = math.hypot(d.location.x - center_fx, d.location.y - center_fy)
                weight = 0
                if getattr(d, 'state', '') == 'moving_to_field' and getattr(d, 'target_id', None) == f.id:
                    weight -= 50.0
                pool.append((dist + weight, d))
            pool.sort(key=lambda t: t[0])

            for i in range(min(needed, len(pool))):
                drone = pool[i][1]
                environment.assign_group(drone, group)
                assigned.add(drone)

        # Step 4: Idle all remaining drones
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")