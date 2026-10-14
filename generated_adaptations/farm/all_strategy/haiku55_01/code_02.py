import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    @staticmethod
    def _distance(drone, point):
        dx = drone.location.x - point[0]
        dy = drone.location.y - point[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        valid = set(group_ids)

        # 1. Threatened fields, highest threat first
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        unassigned = list(drones)
        assignment = {}

        # 2./3. Fill fields in priority order, prioritising the closest drones
        #       and those already committed to the field (stickiness).
        for field in fields:
            group = f"protecting {field.id}"
            if group not in valid:
                continue
            need = int(field.drones_for_full_protection)
            if need <= 0 or not unassigned:
                continue

            center = self._field_center(field)

            def sort_key(d, fid=field.id, c=center):
                committed = (d.target_id == fid and d.state in ("protecting", "moving_to_field"))
                return (0 if committed else 1, self._distance(d, c))

            candidates = sorted(unassigned, key=sort_key)
            chosen = candidates[:need]
            for d in chosen:
                assignment[d] = group
            chosen_set = set(chosen)
            unassigned = [d for d in unassigned if d not in chosen_set]

        # 4. Leftover drones: idle only if no threatened field still needs them
        for d in unassigned:
            assignment[d] = "idle"

        # 5. Every drone is assigned exactly once
        for d in drones:
            environment.assign_group(d, assignment.get(d, "idle"))