from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved adaptation:
    - Prioritize the highest-threat field and select drones by estimated arrival time (distance / speed).
    - Keep drones already protecting a fully protected field in place.
    - Prefer not to pull drones that are actively protecting other fields by adding a small penalty,
      but allow it if needed to protect higher-threat fields faster.
    - After securing the top field, allocate remaining drones to other threatened fields (in threat order).
    - Remaining drones are set to 'idle'.
    """
    DRONE_SPEED = 2.0
    # Penalties to discourage reassigning actively protecting drones, but not forbid it.
    PENALTY_PROTECTING_OTHER = 3.0
    PENALTY_MOVING_OTHER = 0.5

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute center of a field
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: Euclidean distance
        def distance(a_x, a_y, b_x, b_y):
            return math.hypot(a_x - b_x, a_y - b_y)

        # Quick map for group availability
        idle_group = "idle"
        have_idle = idle_group in group_ids

        # Build list of threatened fields sorted by threat_level desc, tie-break by id
        threatened_fields = sorted(
            [f for f in environment.fields if getattr(f, "threat_level", 0) > 0],
            key=lambda f: (-f.threat_level, getattr(f, "id", ""))
        )

        # If no threatened fields: set all drones to idle
        if not threatened_fields:
            target = idle_group if have_idle else (group_ids[0] if group_ids else idle_group)
            for c in components:
                environment.assign_group(c, target)
            return

        # Keep track of assignment decisions: mapping drone -> group_name
        assignments = {}

        # Keep a set/list of drones not yet assigned
        remaining_drones = list(components)

        # For quicker access to drone attributes, define a small helper to compute arrival times
        def arrival_time_to_field(drone, field):
            cx, cy = field_center(field)
            lx = getattr(drone.location, "x", 0.0)
            ly = getattr(drone.location, "y", 0.0)
            dist = distance(lx, ly, cx, cy)
            base_time = dist / self.DRONE_SPEED
            # Add small penalties to discourage pulling drones away from active protections or other commitments
            if getattr(drone, "state", None) == "protecting":
                if getattr(drone, "target_id", None) == getattr(field, "id", None):
                    return 0.0  # already protecting this field
                else:
                    return base_time + self.PENALTY_PROTECTING_OTHER
            elif getattr(drone, "state", None) == "moving_to_field":
                # If moving to this field, arrival is base_time (they are heading there)
                if getattr(drone, "target_id", None) == getattr(field, "id", None):
                    return base_time
                else:
                    # moving elsewhere: small penalty to reflect commitment
                    return base_time + self.PENALTY_MOVING_OTHER
            else:
                # idle or other: no penalty
                return base_time

        # Process fields in threat order
        for field in threatened_fields:
            protect_group = f"protecting {field.id}"
            if protect_group not in group_ids:
                # Can't assign to this group's name; skip to next
                continue

            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Count how many of the remaining_drones are already protecting this field
            already_protecting = [d for d in remaining_drones
                                  if getattr(d, "state", None) == "protecting"
                                  and getattr(d, "target_id", None) == getattr(field, "id", None)]

            num_already = len(already_protecting)

            # If already fully protected by remaining drones, keep those drones assigned
            if num_already >= required:
                # assign exactly those (others in remaining_drones remain unassigned for now)
                for d in already_protecting[:required]:
                    assignments[d] = protect_group
                    remaining_drones.remove(d)
                # Any extra already_protecting beyond required will be left for further allocation (could be unassigned)
                continue

            # Need more drones: compute arrival times for all other remaining drones (excluding already_protecting)
            needed = required - num_already

            candidates = [d for d in remaining_drones if d not in already_protecting]

            # Compute (drone, arrival_time) pairs
            timed = [(d, arrival_time_to_field(d, field)) for d in candidates]
            # Sort by arrival time (earliest arrival first). Tie-breakers: prefer idle, then moving_to_field, then protecting.
            def tie_key(pair):
                d, t = pair
                state = getattr(d, "state", "")
                state_rank = 2
                if state == "idle":
                    state_rank = 0
                elif state == "moving_to_field":
                    state_rank = 1
                elif state == "protecting":
                    state_rank = 3
                return (t, state_rank)
            timed.sort(key=tie_key)

            # Assign already_protecting first
            for d in already_protecting:
                assignments[d] = protect_group
                if d in remaining_drones:
                    remaining_drones.remove(d)

            # Pick top 'needed' from timed
            for d, _t in timed[:needed]:
                assignments[d] = protect_group
                if d in remaining_drones:
                    remaining_drones.remove(d)

            # If we couldn't find enough (e.g., not enough drones), we assigned as many as available.

        # After attempting to protect all threatened fields in order, assign remaining drones to idle
        idle_target = idle_group if have_idle else (group_ids[0] if group_ids else idle_group)
        for d in list(remaining_drones):
            assignments[d] = idle_target

        # Finally, apply assignments via environment.assign_group for every component
        # Ensure every component is explicitly assigned (even if same as before)
        for c in components:
            group = assignments.get(c, idle_target)
            environment.assign_group(c, group)