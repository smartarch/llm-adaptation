import math

# Assuming the base class can be imported as described
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Keep a memory of last group assignment for each drone (by id)
        self.prev_group = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Divide drones into:
        - idle: drones doing nothing
        - protecting {field_id}: drones protecting a specific field

        Strategy:
        - Fully protect the most threatened field first using the closest drones.
        - Do not overprotect a field (respect drones_for_full_protection).
        - If possible, use enough drones to reach at least half the fleet protecting.
        - Use distance-based selection to pick the closest drones for protection.
        - Maintain per-step re-assignments (explicitly re-assign every drone to a group).
        """
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_group[id(c)] = "idle"
            return

        # Identify the most threatened field
        top_field = max(fields_with_threat, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"

        # If the top group isn't a valid group, fall back to idle (robustness)
        if top_group not in group_ids:
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_group[id(c)] = "idle"
            return

        # How many drones are needed to fully protect the top field
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Center of the top field
        top_center = ((top_field.left + top_field.right) / 2.0,
                      (top_field.top + top_field.bottom) / 2.0)

        def distance_to_top(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - top_center[0]
            dy = getattr(loc, "y", 0.0) - top_center[1]
            return math.hypot(dx, dy)

        # Current drones protecting top_field
        current_top = [
            d for d in components
            if getattr(d, "target_id", None) == top_field.id
            and getattr(d, "state", "") in ("protecting", "moving_to_field")
        ]
        current_top_count = len(current_top)

        # Drones not currently protecting top_field
        pool = [d for d in components if d not in current_top]

        # Drones needed to reach full protection for top_field
        needed = max(0, required_top - current_top_count)

        # Sort pool by distance to top_field center
        pool_sorted = sorted(pool, key=distance_to_top)

        # Assign the closest needed drones to top_field
        for d in pool_sorted[:needed]:
            environment.assign_group(d, top_group)
            self.prev_group[id(d)] = top_group

        # If we have more drones currently protecting top_field than needed, move the farthest ones to idle
        if current_top_count > required_top:
            # Recompute current_top sorted by distance (farthest first)
            current_top_sorted = sorted(current_top, key=distance_to_top, reverse=True)
            to_idle = current_top_sorted[: (current_top_count - required_top)]
            for d in to_idle:
                environment.assign_group(d, "idle")
                self.prev_group[id(d)] = "idle"

        # After top_field allocation, compute how many drones are protecting overall
        protecting_count = sum(1 for d in components if self.prev_group.get(id(d)) == top_group)

        total_drones = len(components)
        half_target = (total_drones + 1) // 2  # at least half (ceil)

        # If we are below half, try to protect other fields in order of threat
        if protecting_count < half_target:
            # Other fields ordered by threat (exclude top_field)
            other_fields = sorted(
                [f for f in fields_with_threat if f.id != top_field.id],
                key=lambda f: f.threat_level,
                reverse=True
            )

            # Drones currently not protecting top_field
            spare = [d for d in components if self.prev_group.get(id(d)) != top_group]

            for field in other_fields:
                if protecting_count >= half_target:
                    break

                other_group = f"protecting {field.id}"
                if other_group not in group_ids:
                    # If the field's group isn't valid, skip to idle
                    other_group = "idle"

                # Current protection for this field
                current_for_field = [
                    d for d in components
                    if self.prev_group.get(id(d), "") == other_group
                ]
                current_count = len(current_for_field)
                max_for_field = int(getattr(field, "drones_for_full_protection", 0))
                needed_field = max(0, max_for_field - current_count)

                if needed_field <= 0:
                    continue

                center = ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

                # Sort spare by distance to this field
                spare_sorted = sorted(
                    spare, key=lambda d: math.hypot(
                        getattr(d.location, "x", 0.0) - center[0],
                        getattr(d.location, "y", "0.0") - center[1]
                    ) if getattr(d, "location", None) is not None else float("inf")
                )

                for d in spare_sorted[:needed_field]:
                    environment.assign_group(d, other_group)
                    self.prev_group[id(d)] = other_group
                    spare.remove(d)
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break

        # Finally, re-assign any drones that still don't have a group (shouldn't happen often)
        for d in components:
            if self.prev_group.get(id(d)) is None:
                environment.assign_group(d, "idle")
                self.prev_group[id(d)] = "idle"