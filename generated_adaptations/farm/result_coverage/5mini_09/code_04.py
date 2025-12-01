from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Drone speed (given)
        DRONE_SPEED = 2.0

        # Helper: get center of a field
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        # Helper: distance from a drone to a field center
        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy)

        # Helper: estimated time to arrive to a field
        def arrival_time(drone, field):
            # If drone is already protecting that field, arrival time 0
            if getattr(drone, "state", None) == "protecting" and drone.target_id == field.id:
                return 0.0
            # Otherwise compute distance / speed
            return distance_to_field(drone, field) / DRONE_SPEED

        # Available fields with positive threat
        all_fields = list(getattr(environment, "fields", []) or [])
        threatened_fields = [f for f in all_fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened field, set all drones idle
        idle_group = "idle"
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Sort fields by descending threat_level (tie-break by id for determinism)
        threatened_fields.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)

        # Prepare structures to track assignments
        assigned_group = {}  # component -> group string

        # Helper to mark a component as assigned to a group
        def mark_assign(comp, group):
            assigned_group[comp] = group

        # Set of components not yet assigned
        unassigned = list(components)

        # Function to count how many unassigned components already are protecting/moving to this field
        def count_already_contributing(field):
            contrib = []
            for c in unassigned:
                if getattr(c, "target_id", None) == field.id and getattr(c, "state", None) in ("protecting", "moving_to_field"):
                    contrib.append(c)
            return contrib

        # Protect fields in order. Highest-threat must be fully protected (or as many as possible).
        for idx, field in enumerate(threatened_fields):
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue  # nothing to assign

            # List of unassigned drones that are already protecting or moving to this field
            already = count_already_contributing(field)
            already_count = len(already)

            # Remove these 'already' drones from unassigned and tentatively assign them to this field
            for c in already:
                mark_assign(c, f"protecting {field.id}")
            unassigned = [c for c in unassigned if c not in already]

            needed = max(0, required - already_count)

            if needed == 0:
                # Field already has sufficient contributors (from state); ensure group name exists
                protecting_group = f"protecting {field.id}"
                if protecting_group not in group_ids:
                    # If group missing (shouldn't happen), revert those 'already' to idle
                    for c in already:
                        assigned_group[c] = idle_group
                # Otherwise keep as assigned
                continue

            # For the highest-threat field (idx == 0) we must use the closest drones to reach full protection,
            # even if that means using most/all drones available.
            # For other fields, only proceed if we can fully meet the requirement with currently available drones.
            available_count = len(unassigned)
            if idx == 0:
                # pick up to 'needed' closest drones by arrival time (may be fewer than needed if not enough drones exist)
                # compute arrival times for all unassigned drones
                sorted_candidates = sorted(unassigned, key=lambda c: arrival_time(c, field))
                to_take = sorted_candidates[:needed] if available_count >= needed else sorted_candidates[:available_count]
            else:
                # only proceed if we can fully satisfy the requirement
                if available_count < needed:
                    # Can't fully protect this secondary field; skip (leave its 'already' contributors assigned earlier if any)
                    # If we had assigned 'already' contributors but cannot reach full protection, it's still beneficial to keep them,
                    # because they were already moving/protecting this field. We'll keep them assigned.
                    continue
                # We can fully protect: pick the nearest 'needed' drones
                sorted_candidates = sorted(unassigned, key=lambda c: arrival_time(c, field))
                to_take = sorted_candidates[:needed]

            # Assign chosen drones to protecting group
            protecting_group = f"protecting {field.id}"
            if protecting_group not in group_ids:
                # fallback to idle if group name invalid
                for c in to_take:
                    mark_assign(c, idle_group)
            else:
                for c in to_take:
                    mark_assign(c, protecting_group)

            # Remove assigned ones from unassigned
            for c in to_take:
                if c in unassigned:
                    unassigned.remove(c)

        # Finally, any components not explicitly assigned are set to idle
        for comp in components:
            group = assigned_group.get(comp, idle_group)
            # Validate group exists; if not, fallback to idle
            if group not in group_ids:
                group = idle_group
            environment.assign_group(comp, group)