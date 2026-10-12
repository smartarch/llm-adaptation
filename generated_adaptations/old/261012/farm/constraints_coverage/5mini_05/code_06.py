from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Strategy:
    - Fully protect the most threatened field using the closest drones.
    - Then try to fully protect other fields (descending threat) using remaining drones (only full sets).
    - If fewer than half of drones are protecting, add extra drones (closest-first to best-fit fields)
      to reach at least half protecting (partial protection allowed here).
    - All other drones are assigned to "idle".
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_between(drone, center):
            dx = drone.location.x - center[0]
            dy = drone.location.y - center[1]
            return math.hypot(dx, dy)

        idle_group = "idle"
        n = len(components)

        # Gather threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, put all drones idle (only if idle group exists)
        if not threatened:
            for comp in components:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
            return

        # Sort threatened by descending threat
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute centers
        centers = {f.id: field_center(f) for f in threatened}

        # Helper: distance of each drone to a given field id
        def distances_to_field(field_id):
            c = centers[field_id]
            return [(dist_between(components[i], c), i) for i in range(n)]

        assignments = {}  # idx -> group_name

        # Step A: Protect the top field with the closest drones
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        top_needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Only proceed if protecting group for top_field is valid
        if top_group in group_ids and top_needed > 0:
            dists = distances_to_field(top_field.id)
            dists.sort(key=lambda x: x[0])
            take = min(top_needed, n)
            for _, idx in dists[:take]:
                assignments[idx] = top_group
        else:
            # If group not available or top_needed == 0, we cannot protect; put all idle
            for comp in components:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
            return

        # Step B: Try to fully protect other fields (prefer full sets)
        for field in threatened[1:]:
            group = f"protecting {field.id}"
            if group not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # count unassigned drones
            unassigned = [i for i in range(n) if i not in assignments]
            if len(unassigned) < required:
                # Not enough unassigned drones to fully protect this field; skip to preserve full protections
                continue
            # pick closest 'required' from unassigned
            center = centers[field.id]
            cand = [(dist_between(components[i], center), i) for i in unassigned]
            cand.sort(key=lambda x: x[0])
            for _, idx in cand[:required]:
                assignments[idx] = group

        # Step C: Ensure at least half of the drones are protecting (assign extra if needed)
        protecting_count = len([i for i in assignments if assignments.get(i, "").startswith("protecting ")])
        min_protect = (n + 1) // 2  # round up to ensure at least half
        if protecting_count < min_protect:
            need_extra = min_protect - protecting_count
            # For each unassigned drone, find best (closest) threatened field group available
            unassigned = [i for i in range(n) if i not in assignments]
            best_choices = []
            for idx in unassigned:
                best_field = None
                best_dist = float("inf")
                for field in threatened:
                    grp = f"protecting {field.id}"
                    if grp not in group_ids:
                        continue
                    d = dist_between(components[idx], centers[field.id])
                    if d < best_dist:
                        best_dist = d
                        best_field = field
                if best_field is not None:
                    best_choices.append((best_dist, idx, best_field))
            # Sort all candidate (distance, idx, field) by distance and pick the closest ones up to need_extra
            best_choices.sort(key=lambda t: t[0])
            for _, idx, field in best_choices[:need_extra]:
                assignments[idx] = f"protecting {field.id}"

        # Step D: Finalize assignments - assign protecting groups (from assignments) and idle for remaining
        for idx in range(n):
            comp = components[idx]
            if idx in assignments:
                grp = assignments[idx]
                # safety check: only assign if grp in group_ids
                if grp in group_ids:
                    environment.assign_group(comp, grp)
                else:
                    # fallback to idle if protecting group invalid
                    if idle_group in group_ids:
                        environment.assign_group(comp, idle_group)
                    else:
                        # final fallback: assign to first available group_id
                        if group_ids:
                            environment.assign_group(comp, group_ids[0])
            else:
                # assign idle if available, else fallback to first group_id
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    if group_ids:
                        environment.assign_group(comp, group_ids[0])