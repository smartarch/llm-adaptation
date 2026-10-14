import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance_to_field(self, location, field):
        cx, cy = self._field_center(field)
        dx = location.x - cx
        dy = location.y - cy
        return math.sqrt(dx * dx + dy * dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # --- 1. Build lookup of fields by id ---
        field_by_id = {f.id: f for f in environment.fields}

        # --- 2. Determine which drones are currently committed to a field ---
        committed = {fid: [] for fid in field_by_id}
        unassigned_drones = []

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in committed:
                committed[tid].append(drone)
            else:
                unassigned_drones.append(drone)

        # --- 3. Sort active fields by threat level descending ---
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # --- 4. Decide assignments field by field (greedy priority) ---
        # final_assignments maps id(drone) -> field_id (or None for idle)
        final_assignments = {}

        for field in active_fields:
            need = field.drones_for_full_protection
            currently_on = committed.get(field.id, [])

            # Keep existing drones up to the required number (stability)
            keep = currently_on[:need]
            excess = currently_on[need:]

            for d in keep:
                final_assignments[id(d)] = field.id
            # Excess drones become available again
            for d in excess:
                unassigned_drones.append(d)

            # If more drones are needed, pull closest from unassigned pool
            still_needed = need - len(keep)
            if still_needed > 0 and unassigned_drones:
                unassigned_drones.sort(
                    key=lambda d: self._distance_to_field(d.location, field)
                )
                to_add = unassigned_drones[:still_needed]
                unassigned_drones = unassigned_drones[still_needed:]
                for d in to_add:
                    final_assignments[id(d)] = field.id

        # --- 5. Release drones from fields with threat == 0 ---
        for field in environment.fields:
            if field.threat_level <= 0:
                for d in committed.get(field.id, []):
                    if id(d) not in final_assignments:
                        unassigned_drones.append(d)

        # --- 6. Second pass: try to protect under-protected fields with leftovers ---
        for field in active_fields:
            need = field.drones_for_full_protection
            already = sum(
                1 for d in components if final_assignments.get(id(d)) == field.id
            )
            deficit = need - already
            if deficit > 0 and unassigned_drones:
                unassigned_drones.sort(
                    key=lambda d: self._distance_to_field(d.location, field)
                )
                to_add = unassigned_drones[:deficit]
                unassigned_drones = unassigned_drones[deficit:]
                for d in to_add:
                    final_assignments[id(d)] = field.id

        # --- 7. Any truly remaining drones go idle ---
        for drone in components:
            assigned_field = final_assignments.get(id(drone))
            if assigned_field is not None:
                group_name = f"protecting {assigned_field}"
                if group_name in group_ids:
                    environment.assign_group(drone, group_name)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")