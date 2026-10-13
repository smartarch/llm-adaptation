import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    @staticmethod
    def _distance_to_field(drone, field):
        """Distance from the drone to the nearest point on the field rectangle."""
        x = drone.location.x
        y = drone.location.y
        dx = max(field.left - x, 0, x - field.right)
        dy = max(field.top - y, 0, y - field.bottom)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        idle_group = "idle"
        assignments = {}
        remaining = set(range(len(components)))

        fields = [
            field
            for field in environment.fields
            if field.threat_level > 0
            and f"protecting {field.id}" in valid_groups
        ]
        fields.sort(key=lambda field: (-field.threat_level, str(field.id)))

        for field in fields:
            group = f"protecting {field.id}"
            required = max(0, math.ceil(field.drones_for_full_protection))
            if required == 0 or not remaining:
                continue

            # Preserve existing assignments when possible.
            incumbents = [
                i for i in remaining
                if components[i].target_id == field.id
            ]

            def distance_key(i):
                return (
                    self._distance_to_field(components[i], field),
                    0 if components[i].target_id == field.id else 1,
                    i,
                )

            if len(incumbents) >= required:
                chosen = sorted(incumbents, key=distance_key)[:required]
            else:
                chosen = list(incumbents)
                needed = required - len(chosen)
                candidates = [i for i in remaining if i not in incumbents]
                chosen.extend(sorted(candidates, key=distance_key)[:needed])

            for i in chosen:
                assignments[i] = group
                remaining.remove(i)

        for i in remaining:
            assignments[i] = idle_group

        # Assign every drone explicitly, including drones staying in their current group.
        for i, drone in enumerate(components):
            environment.assign_group(drone, assignments[i])