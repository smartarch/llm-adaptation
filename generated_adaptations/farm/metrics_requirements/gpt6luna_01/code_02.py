import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        valid_groups = set(group_ids)
        fields = [
            field
            for field in environment.fields
            if field.threat_level > 0
            and f"protecting {field.id}" in valid_groups
        ]

        # A positive-threat field should require at least one drone. Rounding up
        # also handles protection requirements represented as non-integers.
        def requirement(field):
            return max(1, math.ceil(float(field.drones_for_full_protection)))

        def center(field):
            return (
                (float(field.left) + float(field.right)) / 2.0,
                (float(field.top) + float(field.bottom)) / 2.0,
            )

        def distance(drone, field):
            cx, cy = center(field)
            dx = float(drone.location.x) - cx
            dy = float(drone.location.y) - cy
            return dx * dx + dy * dy

        def already_targets(drone, field):
            return drone.target_id is not None and str(drone.target_id) == str(field.id)

        assignments = {}
        remaining_drones = set(range(len(drones)))
        field_slots = {}

        if fields and drones:
            # Stable tie-breaking by field identifier.
            ordered = sorted(
                fields,
                key=lambda field: (-float(field.threat_level), str(field.id)),
            )
            top_field = ordered[0]

            # Allocate the top-threat field first. If the fleet is large enough,
            # it is always fully protected.
            top_count = min(requirement(top_field), len(drones))
            field_slots[top_field.id] = top_count
            remaining_count = len(drones) - top_count

            # Use remaining drones to fully protect as many high-priority fields
            # as possible, without assigning more than a field needs.
            fully_selected = {top_field.id}
            while remaining_count > 0:
                chosen = next(
                    (
                        field
                        for field in ordered[1:]
                        if field.id not in fully_selected
                        and requirement(field) <= remaining_count
                    ),
                    None,
                )
                if chosen is None:
                    break
                field_slots[chosen.id] = requirement(chosen)
                fully_selected.add(chosen.id)
                remaining_count -= requirement(chosen)

            # If there are drones left, concentrate them on the highest-threat
            # field that can still use them rather than spreading partial
            # protection across several fields.
            if remaining_count > 0:
                partial_target = next(
                    (
                        field
                        for field in ordered[1:]
                        if field.id not in fully_selected
                    ),
                    None,
                )
                if partial_target is not None:
                    count = min(remaining_count, requirement(partial_target))
                    field_slots[partial_target.id] = count
                    remaining_count -= count

            # The top-threat field gets the closest drones, based on current
            # locations, even if those drones were previously assigned elsewhere.
            closest = sorted(
                range(len(drones)),
                key=lambda i: (
                    distance(drones[i], top_field),
                    0 if already_targets(drones[i], top_field) else 1,
                    i,
                ),
            )
            for i in closest[:field_slots[top_field.id]]:
                assignments[i] = f"protecting {top_field.id}"
                remaining_drones.discard(i)

            # For other selected fields, reserve drones already targeting that
            # field first. This reduces unnecessary reassignment between calls.
            secondary_fields = [
                field for field in ordered[1:] if field.id in field_slots
            ]
            for field in secondary_fields:
                group = f"protecting {field.id}"
                candidates = sorted(
                    (
                        i for i in remaining_drones
                        if already_targets(drones[i], field)
                    ),
                    key=lambda i: (distance(drones[i], field), i),
                )
                for i in candidates[:field_slots[field.id]]:
                    assignments[i] = group
                    remaining_drones.discard(i)

            # Fill any unfilled slots, preferring a drone's existing assignment
            # and then its distance to the field.
            for field in secondary_fields:
                group = f"protecting {field.id}"
                already_assigned = sum(
                    1 for assigned_group in assignments.values()
                    if assigned_group == group
                )
                needed = field_slots[field.id] - already_assigned
                if needed <= 0:
                    continue

                candidates = sorted(
                    remaining_drones,
                    key=lambda i: (
                        0 if already_targets(drones[i], field) else 1,
                        distance(drones[i], field),
                        i,
                    ),
                )
                for i in candidates[:needed]:
                    assignments[i] = group
                    remaining_drones.discard(i)

        # Explicitly assign every drone on every call, including drones that
        # remain in their current group.
        for i, drone in enumerate(drones):
            group = assignments.get(i, "idle")
            if group not in valid_groups:
                group = "idle"
            environment.assign_group(drone, group)