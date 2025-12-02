import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Constants
        DRONE_SPEED = 2.0
        PENALTY_PROTECTING_OTHER = 10000.0  # very discouraging to pull from active protection
        PENALTY_MOVING_OTHER = 50.0         # discourage pulling drones en-route to other fields
        # Safety fallback for idle group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else None)
        if idle_group is None:
            # No groups at all: nothing to do
            return

        def safe_assign(comp, group):
            if group in group_ids:
                environment.assign_group(comp, group)
            else:
                environment.assign_group(comp, idle_group)

        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(comp, center):
            dx = comp.location.x - center[0]
            dy = comp.location.y - center[1]
            return math.hypot(dx, dy)

        # Fields with threat > 0
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threats: assign all drones idle
            for c in components:
                safe_assign(c, idle_group)
            return

        # Sort fields by descending threat, tie-break by id
        threat_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        highest = threat_fields[0]
        highest_center = center_of(highest)
        try:
            required_high = int(math.ceil(highest.drones_for_full_protection))
        except Exception:
            required_high = 1
        highest_group = f"protecting {highest.id}"
        # If protecting group for highest is missing, best we can do is idle everyone
        if highest_group not in group_ids:
            for c in components:
                safe_assign(c, idle_group)
            return

        # Helper: compute penalized arrival time for drone to a given field center
        def penalized_arrival(comp, field_center, field_target_id=None):
            # travel time estimate
            d = dist(comp, field_center)
            travel_time = d / DRONE_SPEED
            penalty = 0.0
            # If drone is already protecting the same field -> arrival_time = 0
            if comp.state == "protecting":
                if comp.target_id == field_target_id:
                    travel_time = 0.0
                else:
                    # protecting some other field -> discourage moving it
                    penalty += PENALTY_PROTECTING_OTHER
            elif comp.state == "moving_to_field":
                if comp.target_id != field_target_id:
                    penalty += PENALTY_MOVING_OTHER
                # if moving to same target, no penalty (they're already headed there)
            # idle has no penalty
            return travel_time + penalty

        # Build list of all drones with arrival times to highest
        comps = list(components)
        comp_info = []
        for c in comps:
            arrival = penalized_arrival(c, highest_center, field_target_id=highest.id)
            comp_info.append((c, arrival))

        # Keep drones already protecting highest first (they are preferred)
        protecting_high = [c for c in comps if c.state == "protecting" and c.target_id == highest.id]
        assigned_ids = set()
        # Assign those protecting_high to highest group (they are already there)
        for c in protecting_high:
            safe_assign(c, highest_group)
            assigned_ids.add(id(c))

        # Determine how many still needed
        need = max(0, required_high - len(protecting_high))
        if need > 0:
            # Consider other drones sorted by penalized arrival time
            candidates = [(c, arrival) for (c, arrival) in comp_info if id(c) not in assigned_ids]
            candidates.sort(key=lambda x: x[1])  # sort by penalized arrival
            for c, _ in candidates[:need]:
                safe_assign(c, highest_group)
                assigned_ids.add(id(c))

        # Now handle remaining drones: try to assign them to protect other fields.
        # For each other field in descending threat order, prefer drones already protecting/moving to it,
        # otherwise choose by penalized arrival (with target_id set to that field to avoid penalizing those heading there).
        remaining = [c for c in comps if id(c) not in assigned_ids]

        # Precompute centers
        field_centers = {f.id: center_of(f) for f in threat_fields}

        # For each field (excluding highest) attempt to get it protected (or partially protected)
        for field in threat_fields[1:]:
            if not remaining:
                break
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            try:
                req = int(math.ceil(field.drones_for_full_protection))
            except Exception:
                req = 1
            # Drones already protecting this field among remaining
            already_protecting = [c for c in remaining if c.state == "protecting" and c.target_id == field.id]
            # Assign those to this group
            for c in already_protecting:
                safe_assign(c, group_name)
                assigned_ids.add(id(c))
            # compute how many more needed
            need = max(0, req - len(already_protecting))
            if need == 0:
                remaining = [c for c in remaining if id(c) not in assigned_ids]
                continue
            # From remaining, compute penalized arrival to this field
            cand_list = []
            for c in remaining:
                if id(c) in assigned_ids:
                    continue
                arrival = penalized_arrival(c, field_centers[field.id], field_target_id=field.id)
                cand_list.append((c, arrival))
            cand_list.sort(key=lambda x: x[1])
            # Choose up to 'need' best candidates but avoid taking ones with huge penalty unless necessary
            taken = 0
            for c, arrival in cand_list:
                # If arrival is dominated by penalty (very large), and we still have many fields to consider,
                # it might be better to leave these drones idle. But to reduce damage, we'll still take them if needed.
                safe_assign(c, group_name)
                assigned_ids.add(id(c))
                taken += 1
                if taken >= need:
                    break
            remaining = [c for c in remaining if id(c) not in assigned_ids]

        # For any leftovers, try to preserve their current intention:
        # - If a drone is moving_to_field, assign it to that protecting group (if exists).
        # - If a drone is protecting some other field, keep it there.
        # - Otherwise set idle.
        for c in remaining:
            if c.state == "moving_to_field" and c.target_id is not None:
                g = f"protecting {c.target_id}"
                if g in group_ids:
                    safe_assign(c, g)
                    assigned_ids.add(id(c))
                    continue
            if c.state == "protecting" and c.target_id is not None:
                g = f"protecting {c.target_id}"
                if g in group_ids:
                    safe_assign(c, g)
                    assigned_ids.add(id(c))
                    continue
            # otherwise idle
            safe_assign(c, idle_group)
            assigned_ids.add(id(c))

        # Final check: make sure every drone was assigned
        for c in comps:
            if id(c) not in assigned_ids:
                safe_assign(c, idle_group)
                assigned_ids.add(id(c))