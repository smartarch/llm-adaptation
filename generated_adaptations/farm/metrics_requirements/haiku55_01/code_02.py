import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    @classmethod
    def _distance(cls, drone, field):
        cx, cy = cls._field_center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        drones = list(components)

        # Threatened fields, most threatened first
        fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: -f.threat_level,
        )

        # drone -> field id mapping (identity-based to be safe with component objects)
        plan = {}  # id(drone) -> field id
        remaining = list(drones)

        for rank, field in enumerate(fields):
            if not remaining:
                break

            cap = max(1, int(round(field.drones_for_full_protection)))

            if rank == 0:
                # Most threatened field: closest drones only
                chosen = sorted(remaining, key=lambda d: self._distance(d, field))[:cap]
            else:
                # Stickiness: prefer drones already targeting this field, then nearest
                sticky = sorted(
                    [d for d in remaining if d.target_id == field.id],
                    key=lambda d: self._distance(d, field),
                )
                others = sorted(
                    [d for d in remaining if d.target_id != field.id],
                    key=lambda d: self._distance(d, field),
                )
                chosen = (sticky + others)[:cap]

            chosen_ids = {id(d) for d in chosen}
            for d in chosen:
                plan[id(d)] = field.id
            remaining = [d for d in remaining if id(d) not in chosen_ids]

        # Apply assignments
        for drone in drones:
            field_id = plan.get(id(drone))
            if field_id is not None:
                group = f"protecting {field_id}"
                if group in valid_groups:
                    environment.assign_group(drone, group)
                    continue
            environment.assign_group(drone, "idle")