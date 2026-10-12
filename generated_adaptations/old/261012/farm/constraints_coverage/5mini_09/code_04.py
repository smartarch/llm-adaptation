from math import ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group_name(fid):
            return f"protecting {fid}"

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else idle_group

        # Consider only fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats -> all idle
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Prepare field centers and easy lookup
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Sort fields by descending threat_level (tie broken by original order)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper to compute squared distance from drone to a field
        def sq_dist_drone_field(drone, field_id):
            lx = getattr(drone.location, "x", 0)
            ly = getattr(drone.location, "y", 0)
            cx, cy = field_centers[field_id]
            dx = lx - cx
            dy = ly - cy
            return dx * dx + dy * dy

        total_drones = len(components)
        desired_protecting = ceil(total_drones / 2.0)

        # Track assignments: drone -> field_id (for protecting) or None
        assignment = {d: None for d in components}

        # Available drones set (those not yet assigned to a protecting field)
        available = set(components)

        # First: ensure the top field is fully protected (highest threat)
        top_field = threatened_fields[0]
        top_group = protecting_group_name(top_field.id)
        # If protecting group not in group_ids, we cannot assign to it; treat as skip -> all idle
        if top_group not in group_ids:
            # fallback: cannot protect any field since expected group missing
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Drones already targeting the field count as assigned
        already_for_top = [d for d in components if getattr(d, "target_id", None) == top_field.id]
        # Keep only those that are still in available set
        for d in already_for_top:
            assignment[d] = top_field.id
            if d in available:
                available.remove(d)

        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        needed_top = max(0, required_top - len(already_for_top))

        # Select closest available drones to fill the top field requirement
        if needed_top > 0 and available:
            avail_list = list(available)
            avail_list.sort(key=lambda d: sq_dist_drone_field(d, top_field.id))
            to_take = avail_list[:needed_top]
            for d in to_take:
                assignment[d] = top_field.id
                available.remove(d)

        # Next: try to fully protect other fields in descending threat order
        for f in threatened_fields[1:]:
            group_name = protecting_group_name(f.id)
            if group_name not in group_ids:
                continue  # cannot assign to this field's protecting group
            # Count drones already targeting this field (and not already assigned to another protecting field)
            already = [d for d in components if getattr(d, "target_id", None) == f.id and assignment.get(d) is None]
            for d in already:
                assignment[d] = f.id
                if d in available:
                    available.remove(d)
            required = int(getattr(f, "drones_for_full_protection", 0))
            needed = max(0, required - sum(1 for d in assignment if assignment[d] == f.id))
            if needed > 0 and available:
                avail_list = list(available)
                avail_list.sort(key=lambda d: sq_dist_drone_field(d, f.id))
                take = avail_list[:needed]
                for d in take:
                    assignment[d] = f.id
                    available.remove(d)

        # After trying to fully protect as many fields as possible, ensure at least half drones are protecting
        current_protecting = sum(1 for d in assignment if assignment[d] is not None)
        if current_protecting < desired_protecting and available:
            # Assign remaining available drones (closest-first) to any threatened field (choose by closeness)
            avail_list = list(available)
            # For each available drone, find its closest threatened field (whose protect group exists)
            drone_best = []
            valid_field_ids = [f.id for f in threatened_fields if protecting_group_name(f.id) in group_ids]
            if valid_field_ids:
                for d in avail_list:
                    best_field = min(valid_field_ids, key=lambda fid: sq_dist_drone_field(d, fid))
                    dist = sq_dist_drone_field(d, best_field)
                    drone_best.append((d, best_field, dist))
                # Sort drones by dist ascending so we assign closest ones first
                drone_best.sort(key=lambda tup: tup[2])
                idx = 0
                while current_protecting < desired_protecting and idx < len(drone_best):
                    d, fid, _ = drone_best[idx]
                    # assign
                    assignment[d] = fid
                    if d in available:
                        available.remove(d)
                    current_protecting += 1
                    idx += 1

        # Final assignment: any remaining available drones remain idle
        for d in components:
            fid = assignment.get(d)
            if fid is not None:
                grp = protecting_group_name(fid)
                # If group isn't available for some reason, fallback to idle
                if grp in group_ids:
                    environment.assign_group(d, grp)
                else:
                    environment.assign_group(d, idle_group)
            else:
                environment.assign_group(d, idle_group)