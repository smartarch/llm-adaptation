from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        idle_group = "idle"

        # Only fields with positive threat have protection groups.
        fields = [
            field for field in environment.fields
            if field.threat_level > 0
            and f"protecting {field.id}" in valid_groups
        ]
        fields.sort(key=lambda field: (-field.threat_level, str(field.id)))

        drones = list(components)
        remaining = list(drones)
        allocations = []

        # Allocate full protection to the highest-threat fields first. If the
        # remaining fleet cannot fully protect the next field, use the remaining
        # drones there rather than leaving them idle.
        for field in fields:
            needed = max(0, int(field.drones_for_full_protection))
            if needed == 0 or not remaining:
                continue

            count = min(needed, len(remaining))
            allocations.append((field, count))
            # Reserve these drones in the selection pass below.
            if count == len(remaining):
                break

            # This placeholder is not used to choose drones; it records the
            # planned capacity while allowing later fields to be considered.
            remaining = remaining[count:]

        # Rebuild the plan using drone counts, without removing specific drones.
        total_drones = len(drones)
        planned = []
        left = total_drones
        for field in fields:
            needed = max(0, int(field.drones_for_full_protection))
            if needed == 0 or left == 0:
                continue
            count = min(needed, left)
            planned.append((field, count))
            left -= count

        unassigned = list(drones)
        assignments = {}

        def distance_to_field(drone, field):
            location = getattr(drone, "location", None)
            if location is None:
                return float("inf")
            x = (field.left + field.right) / 2.0
            y = (field.top + field.bottom) / 2.0
            dx = getattr(location, "x", 0.0) - x
            dy = getattr(location, "y", 0.0) - y
            return (dx * dx + dy * dy) ** 0.5

        for field, count in planned:
            group = f"protecting {field.id}"
            if count <= 0 or group not in valid_groups:
                continue

            # Retain drones already targeting this field where possible.
            incumbents = [
                drone for drone in unassigned
                if str(getattr(drone, "target_id", None)) == str(field.id)
            ]
            incumbents.sort(key=lambda drone: distance_to_field(drone, field))

            chosen = incumbents[:count]
            chosen_ids = {id(drone) for drone in chosen}

            # Fill any remaining slots with the closest available drones.
            candidates = [
                drone for drone in unassigned
                if id(drone) not in chosen_ids
            ]
            candidates.sort(key=lambda drone: distance_to_field(drone, field))
            chosen.extend(candidates[:max(0, count - len(chosen))])

            for drone in chosen:
                assignments[id(drone)] = group
            chosen_ids = {id(drone) for drone in chosen}
            unassigned = [
                drone for drone in unassigned if id(drone) not in chosen_ids
            ]

        # Explicitly assign every drone, including drones that remain idle.
        for drone in drones:
            group = assignments.get(id(drone), idle_group)
            if group not in valid_groups:
                group = idle_group
            environment.assign_group(drone, group)