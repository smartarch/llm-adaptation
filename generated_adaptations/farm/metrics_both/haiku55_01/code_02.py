import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _field_center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone, field):
        cx, cy = self._field_center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        drones = list(components)

        # Fields that currently attract birds, most threatened first
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        # drone key (index) -> field id
        assignment = {}
        unassigned = list(range(len(drones)))
        skipped = []  # fields that could not be fully protected, in threat order

        for rank, field in enumerate(fields):
            need = max(0, int(field.drones_for_full_protection))
            if need == 0:
                continue

            if len(unassigned) < need:
                if rank == 0:
                    # Most threatened field: partial protection with everything is still better than none
                    for i in unassigned:
                        assignment[i] = field.id
                    unassigned = []
                    break
                skipped.append(field)
                continue

            if rank == 0:
                # Most threatened field gets the closest drones
                ordered = sorted(unassigned, key=lambda i: self._distance(drones[i], field))
            else:
                # Keep drones already on this field (stickiness), then by distance
                ordered = sorted(
                    unassigned,
                    key=lambda i: (
                        0 if drones[i].target_id == field.id else 1,
                        self._distance(drones[i], field),
                    ),
                )

            chosen = ordered[:need]
            for i in chosen:
                assignment[i] = field.id
            chosen_set = set(chosen)
            unassigned = [i for i in unassigned if i not in chosen_set]

        # Leftover drones cannot fully protect any remaining field.
        # Send them to the most threatened skipped field (partial help, no idle drones).
        # Leftover count is always below that field's need, so this never overprotects.
        if unassigned and skipped:
            target = skipped[0]
            ordered = sorted(unassigned, key=lambda i: self._distance(drones[i], target))
            for i in ordered:
                assignment[i] = target.id
            unassigned = []

        # Apply group assignments
        for i, drone in enumerate(drones):
            field_id = assignment.get(i)
            group = f"protecting {field_id}" if field_id is not None else "idle"
            if group not in valid_groups:
                group = "idle"
            environment.assign_group(drone, group)