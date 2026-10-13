import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        idle_group = "idle" if "idle" in valid_groups else (
            group_ids[0] if group_ids else None
        )

        fields = [
            field for field in environment.fields
            if field.threat_level > 0
            and f"protecting {field.id}" in valid_groups
        ]
        fields.sort(key=lambda field: field.threat_level, reverse=True)

        drones = list(components)
        assignments = {}

        # Work out how many drones each field needs, and allocate in threat order.
        available = set(range(len(drones)))

        for field in fields:
            required = max(
                0, int(math.ceil(float(field.drones_for_full_protection)))
            )
            if required == 0:
                continue

            center_x = (field.left + field.right) / 2
            center_y = (field.top + field.bottom) / 2

            def drone_priority(index):
                drone = drones[index]
                already_targeting = drone.target_id == field.id
                dx = drone.location.x - center_x
                dy = drone.location.y - center_y
                distance_squared = dx * dx + dy * dy

                # Retain drones already committed to this field; otherwise use
                # the nearest available drones.
                return (0 if already_targeting else 1, distance_squared, index)

            chosen = sorted(available, key=drone_priority)[:required]
            group = f"protecting {field.id}"

            for index in chosen:
                assignments[index] = group
                available.remove(index)

        # Any drones left after covering all field requirements are idle.
        for index in available:
            assignments[index] = idle_group

        # Explicitly assign every component on every call, including drones
        # that remain in their current group.
        for index, drone in enumerate(drones):
            environment.assign_group(drone, assignments[index])