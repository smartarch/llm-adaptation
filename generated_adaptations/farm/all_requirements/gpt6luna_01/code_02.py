import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_assignments = {}

    @staticmethod
    def _required_drones(field):
        """Return a safe integer number of drones needed for full protection."""
        value = getattr(field, "drones_for_full_protection", 1)
        try:
            return max(1, int(math.ceil(float(value))))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _distance_to_field(drone, field):
        """Euclidean distance from a drone to the nearest point of a field."""
        location = getattr(drone, "location", None)
        if location is None:
            return float("inf")

        x = getattr(location, "x", None)
        y = getattr(location, "y", None)
        if x is None or y is None:
            return float("inf")

        dx = max(field.left - x, 0, x - field.right)
        dy = max(field.top - y, 0, y - field.bottom)
        return math.hypot(dx, dy)

    @staticmethod
    def _target_group(field):
        return f"protecting {field.id}"

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        valid_groups = set(group_ids)
        idle_group = "idle"

        # Only positive-threat fields have valid protection groups.
        fields = [
            field for field in environment.fields
            if field.threat_level > 0
            and self._target_group(field) in valid_groups
        ]

        assignments = {}
        field_allocations = {field.id: [] for field in fields}
        remaining = list(drones)

        if fields and drones:
            # The highest-threat field is an absolute priority. Select its
            # closest available drones, breaking distance ties in favor of
            # drones already assigned there.
            fields_by_threat = sorted(
                fields,
                key=lambda field: (-field.threat_level, str(field.id)),
            )
            top_field = fields_by_threat[0]
            top_group = self._target_group(top_field)
            top_count = min(self._required_drones(top_field), len(remaining))

            top_drones = sorted(
                remaining,
                key=lambda drone: (
                    self._distance_to_field(drone, top_field),
                    0 if getattr(drone, "target_id", None) == top_field.id else 1,
                ),
            )[:top_count]

            for drone in top_drones:
                assignments[id(drone)] = top_group
                field_allocations[top_field.id].append(drone)
                remaining.remove(drone)

            # Fully protect additional fields when possible. For these fields,
            # retaining a drone's current target takes precedence over distance.
            for field in fields_by_threat[1:]:
                needed = self._required_drones(field)
                if len(remaining) < needed:
                    continue

                group = self._target_group(field)
                selected = sorted(
                    remaining,
                    key=lambda drone: (
                        0 if getattr(drone, "target_id", None) == field.id else 1,
                        0 if self._last_assignments.get(id(drone)) == group else 1,
                        self._distance_to_field(drone, field),
                    ),
                )[:needed]

                for drone in selected:
                    assignments[id(drone)] = group
                    field_allocations[field.id].append(drone)
                    remaining.remove(drone)

            # Use spare drones for partial protection without overprotecting.
            # First concentrate partial protection on the most threatened
            # eligible field; add another partial field only if needed to keep
            # at least half the fleet active.
            target_active_count = (len(drones) + 1) // 2
            while remaining:
                active_count = len(drones) - len(remaining)
                if active_count >= target_active_count:
                    break

                candidates = [
                    field for field in fields
                    if len(field_allocations[field.id])
                    < self._required_drones(field)
                ]
                if not candidates:
                    break

                # Prefer the most threatened field that can take a partial
                # assignment. A field needing just one more drone is still
                # eligible, since this assignment completes its protection.
                candidates.sort(
                    key=lambda field: (
                        -field.threat_level,
                        0 if any(
                            getattr(drone, "target_id", None) == field.id
                            for drone in remaining
                        ) else 1,
                        str(field.id),
                    )
                )
                field = candidates[0]
                group = self._target_group(field)
                slots = self._required_drones(field) - len(
                    field_allocations[field.id]
                )
                count = min(slots, len(remaining))

                selected = sorted(
                    remaining,
                    key=lambda drone: (
                        0 if getattr(drone, "target_id", None) == field.id else 1,
                        0 if self._last_assignments.get(id(drone)) == group else 1,
                        self._distance_to_field(drone, field),
                    ),
                )[:count]

                if not selected:
                    break

                for drone in selected:
                    assignments[id(drone)] = group
                    field_allocations[field.id].append(drone)
                    remaining.remove(drone)

        # Every drone is explicitly assigned on every call. Any drone not
        # allocated to a threatened field is idle.
        for drone in drones:
            group = assignments.get(id(drone), idle_group)
            if group not in valid_groups:
                group = idle_group
            environment.assign_group(drone, group)
            assignments[id(drone)] = group

        self._last_assignments = assignments