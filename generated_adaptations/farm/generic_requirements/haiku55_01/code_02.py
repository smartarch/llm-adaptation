import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Threat-ranked greedy allocation with hysteresis.

    - Threatened fields are processed in descending threat order.
    - Each field receives up to `drones_for_full_protection` drones, so the
      most threatened fields are fully protected first and never overprotected.
    - The most threatened field gets the closest drones (pure distance).
    - Lower-ranked fields prefer drones already heading to them (hysteresis),
      which reduces field switching.
    - Leftover drones are only idle if all threatened fields are already covered.
    """

    HYSTERESIS_FRACTION = 0.1  # fraction of farm span used as stickiness bonus

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone, field):
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _farm_span(self, fields):
        if not fields:
            return 1.0
        left = min(f.left for f in fields)
        right = max(f.right for f in fields)
        top = min(f.top for f in fields)
        bottom = max(f.bottom for f in fields)
        span = math.hypot(right - left, bottom - top)
        return span if span > 0 else 1.0

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        all_fields = list(environment.fields)
        threatened = [f for f in all_fields if f.threat_level > 0]
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        hysteresis = self.HYSTERESIS_FRACTION * self._farm_span(all_fields)

        assignment = {}  # drone index -> group name
        available = list(range(len(drones)))

        for rank, field in enumerate(threatened):
            if not available:
                break

            need = max(1, int(field.drones_for_full_protection))

            if rank == 0:
                # Most threatened field: strictly the closest drones.
                def key(i, field=field):
                    return self._distance(drones[i], field)
            else:
                # Lower-ranked fields: prefer drones already targeting them.
                def key(i, field=field):
                    bonus = hysteresis if drones[i].target_id == field.id else 0.0
                    return self._distance(drones[i], field) - bonus

            ranked = sorted(available, key=key)
            chosen = ranked[:need]
            group = f"protecting {field.id}"
            for i in chosen:
                assignment[i] = group

            chosen_set = set(chosen)
            available = [i for i in available if i not in chosen_set]

        # Any drones not needed for protection go idle.
        for i in available:
            assignment[i] = "idle"

        # Every drone must be explicitly assigned.
        for i, drone in enumerate(drones):
            group = assignment.get(i, "idle")
            environment.assign_group(drone, group)