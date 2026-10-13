import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        drones = list(components)
        assigned = set()

        def distance_to_field(drone, field):
            """Estimate travel distance to the center of a field."""
            x = drone.location.x
            y = drone.location.y
            center_x = (field.left + field.right) / 2
            center_y = (field.top + field.bottom) / 2
            return math.hypot(x - center_x, y - center_y)

        fields = [
            field for field in environment.fields
            if field.threat_level > 0
            and f"protecting {field.id}" in valid_groups
        ]
        fields.sort(key=lambda field: (-field.threat_level, str(field.id)))

        for field in fields:
            group = f"protecting {field.id}"
            required = max(0, math.ceil(field.drones_for_full_protection))
            slots = min(required, len(drones) - len(assigned))

            if slots == 0:
                continue

            available = [
                i for i in range(len(drones))
                if i not in assigned
            ]

            # Preserve drones already serving this field where possible.
            incumbents = [
                i for i in available
                if drones[i].target_id == str(field.id)
            ]
            incumbents.sort(key=lambda i: distance_to_field(drones[i], field))

            if len(incumbents) >= slots:
                selected = incumbents[:slots]
            else:
                selected = list(incumbents)
                remaining_slots = slots - len(selected)
                other_drones = [
                    i for i in available
                    if i not in selected
                ]
                other_drones.sort(key=lambda i: distance_to_field(drones[i], field))
                selected.extend(other_drones[:remaining_slots])

            for i in selected:
                environment.assign_group(drones[i], group)
                assigned.add(i)

        # Explicitly assign every remaining drone, including drones that
        # should stay idle.
        for i, drone in enumerate(drones):
            if i not in assigned:
                environment.assign_group(drone, "idle")