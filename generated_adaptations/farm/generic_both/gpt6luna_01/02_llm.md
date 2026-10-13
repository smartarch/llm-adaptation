The strategy prioritizes fields by threat, fully protecting them in that order whenever enough drones are available. For the most threatened field, it selects the closest drones; for subsequent fields, it prefers drones already assigned there to reduce unnecessary travel. If there aren’t enough drones to fully protect the next field, it assigns the remaining drones there rather than spreading partial protection across multiple fields. Any surplus drones remain idle. Every drone is explicitly assigned on every call.

```py
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    @staticmethod
    def _distance_to_field(drone, field):
        """Distance from a drone to the nearest point of a field's rectangle."""
        x = drone.location.x
        y = drone.location.y

        dx = max(field.left - x, 0, x - field.right)
        dy = max(field.top - y, 0, y - field.bottom)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        idle_group = "idle"

        threatened_fields = [
            field for field in environment.fields
            if field.threat_level > 0
        ]
        threatened_fields.sort(
            key=lambda field: (-field.threat_level, str(field.id))
        )

        # Default every drone to idle; assignments below allocate protection.
        assignments = {drone: idle_group for drone in components}
        available = set(components)

        for field_index, field in enumerate(threatened_fields):
            group = f"protecting {field.id}"
            if group not in valid_groups or not available:
                continue

            required = max(
                0, int(math.ceil(float(field.drones_for_full_protection)))
            )
            if required == 0:
                continue

            count = min(required, len(available))

            if field_index == 0:
                # The highest-threat field gets the closest available drones.
                # Existing assignments break distance ties in favor of stability.
                chosen = sorted(
                    available,
                    key=lambda drone: (
                        self._distance_to_field(drone, field),
                        0 if drone.target_id == field.id else 1,
                    ),
                )[:count]
            else:
                # Preserve existing assignments to this field where possible,
                # then choose the nearest remaining drones.
                chosen = sorted(
                    available,
                    key=lambda drone: (
                        0 if drone.target_id == field.id else 1,
                        self._distance_to_field(drone, field),
                    ),
                )[:count]

            for drone in chosen:
                assignments[drone] = group
                available.remove(drone)

            # If there weren't enough drones to fully protect this field, all
            # remaining drones have been used here; don't spread them thinner.

        # Explicitly assign every component, including drones whose assignment
        # remains unchanged and drones that should be idle.
        for drone in components:
            group = assignments[drone]
            if group not in valid_groups:
                group = idle_group
            environment.assign_group(drone, group)
```