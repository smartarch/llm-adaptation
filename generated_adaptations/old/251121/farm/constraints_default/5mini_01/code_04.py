from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total_drones = len(drones)

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: euclidean distance from drone to (x,y)
        def dist_to_point(drone, x, y):
            dx = getattr(drone.location, "x", 0) - x
            dy = getattr(drone.location, "y", 0) - y
            return math.hypot(dx, dy)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats -> all idle
            for d in drones:
                environment.assign_group(d, "idle")
            return

        # Minimum number of protecting drones we aim for (at least half)
        min_protect = ceil(total_drones / 2.0)

        # Sort fields by descending threat, tie-break by id
        threatened.sort(key=lambda f: (f.threat_level, f.id), reverse=True)

        # Build mapping of current protecting drones by field id
        protecting_by_field = {}
        for f in threatened:
            protecting_by_field[f.id] = [
                d for d in drones
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
            ]

        # Initialize assignment map: keep existing protections by default
        assigned = {}  # drone -> group_name
        for d in drones:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                assigned[d] = f"protecting {d.target_id}"
            else:
                assigned[d] = None

        # Helper: list of drones currently assigned to a given group name
        def currently_assigned_to(group_name):
            return [d for d, g in assigned.items() if g == group_name]

        # Helper: produce candidate lists for a target field (prefer not to steal from other protections)
        def candidate_lists_for_field(field):
            field_center = center_of(field)
            unassigned = [d for d in drones if assigned[d] is None]
            # Categorize unassigned by state and proximity
            unassigned_idle = [d for d in unassigned if getattr(d, "state", None) == "idle"]
            unassigned_moving_to = [d for d in unassigned if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == field.id]
            unassigned_moving_other = [d for d in unassigned if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) != field.id]
            unassigned_other = [d for d in unassigned if d not in unassigned_idle and d not in unassigned_moving_to and d not in unassigned_moving_other]

            # Sort each by distance to field center (closest first)
            for lst in (unassigned_idle, unassigned_moving_to, unassigned_moving_other, unassigned_other):
                lst.sort(key=lambda d: dist_to_point(d, field_center[0], field_center[1]))
            return unassigned_idle, unassigned_moving_to, unassigned_moving_other, unassigned_other

        # Helper: candidate protecting drones from other fields to reassign (steal) if absolutely necessary.
        # Prefer stealing from fields with lower threat_level.
        def stealing_candidates(field):
            # drones assigned to other protecting groups
            candidates = [d for d, g in assigned.items() if g is not None and g != f"protecting {field.id}"]
            # Annotate with (source_field_threat, distance_to_target) to sort: prefer low threat source and close to target
            annot = []
            field_center = center_of(field)
            # Map group->field threat for quick lookup
            group_to_threat = {}
            for f in threatened:
                group_to_threat[f"protecting {f.id}"] = getattr(f, "threat_level", 0)
            for d in candidates:
                grp = assigned[d]
                source_threat = group_to_threat.get(grp, 0)
                dist = dist_to_point(d, field_center[0], field_center[1])
                annot.append((source_threat, dist, d))
            # Sort by source_threat ascending (prefer stealing from low-threat), then distance ascending
            annot.sort(key=lambda x: (x[0], x[1]))
            return [a[2] for a in annot]

        # Assign drones to fields in priority order
        # First: ensure highest-threat field is fully protected (using preferences)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        # Count currently assigned to top
        assigned_top = currently_assigned_to(top_group)
        num_assigned_top = len(assigned_top)

        # If fewer than required, add candidates
        if num_assigned_top < required_top:
            need = required_top - num_assigned_top
            idle, moving_to, moving_other, other = candidate_lists_for_field(top_field)
            selected = []
            for seq in (idle, moving_to, moving_other, other):
                for d in seq:
                    if need <= 0:
                        break
                    selected.append(d)
                    need -= 1
                if need <= 0:
                    break
            # If still need and we have to steal from other protections, do so (but prefer low-threat sources)
            if need > 0:
                steal_list = stealing_candidates(top_field)
                for d in steal_list:
                    if need <= 0:
                        break
                    # Do not steal a drone that is the only protector of its current field if that field has higher or equal threat.
                    # (Simple heuristic) If the source field has more threat than top_field, skip stealing from it.
                    # Determine source field threat:
                    src_group = assigned[d]
                    # map group to source field object
                    # find source field object if exists
                    src_field_id = None
                    if isinstance(src_group, str) and src_group.startswith("protecting "):
                        src_field_id = src_group[len("protecting "):]
                    src_field_obj = next((f for f in threatened if f.id == src_field_id), None)
                    if src_field_obj and getattr(src_field_obj, "threat_level", 0) > getattr(top_field, "threat_level", 0):
                        # don't steal from higher-threat sources
                        continue
                    selected.append(d)
                    need -= 1
            # Assign selected to top group
            for d in selected:
                assigned[d] = top_group

        # After top field, try to protect other fields in descending threat order, preserving existing protectors
        # Aim to reach min_protect in total protected drones, and fully protect fields if possible
        def total_protecting_count():
            return sum(1 for g in assigned.values() if g is not None)

        # Ensure top group's drones are explicitly kept (already done by assigned mapping)
        # Iterate other fields
        for field in threatened[1:]:
            if total_protecting_count() >= min_protect:
                break  # already satisfied minimum protection
            group_name = f"protecting {field.id}"
            required = int(getattr(field, "drones_for_full_protection", 0))
            cur_assigned = len(currently_assigned_to(group_name))
            # Because we initialized assigned with existing protectors, cur_assigned is accurate
            need = max(0, required - cur_assigned)
            if need == 0:
                continue  # already fully protected
            # Candidate unassigned lists
            idle, moving_to, moving_other, other = candidate_lists_for_field(field)
            selected = []
            for seq in (idle, moving_to, moving_other, other):
                for d in seq:
                    if total_protecting_count() + len(selected) >= min_protect:
                        break
                    if need <= 0:
                        break
                    selected.append(d)
                    need -= 1
                if total_protecting_count() + len(selected) >= min_protect or need <= 0:
                    break
            # If still need to fully protect this field and we're allowed to steal (only if we still haven't reached min_protect after using unassigned),
            # and if there are no unassigned drones left to reach min_protect, then consider stealing from lower-threat assignments.
            if need > 0 and total_protecting_count() + len(selected) < min_protect:
                # attempt to steal minimal necessary from protections of lower threat fields
                steal_list = stealing_candidates(field)
                for d in steal_list:
                    if total_protecting_count() + len(selected) >= min_protect:
                        break
                    # avoid stealing from top_field or this field itself
                    if assigned[d] == f"protecting {top_field.id}" or assigned[d] == group_name:
                        continue
                    selected.append(d)
                    need -= 1
                    if need <= 0:
                        break
            # Assign selected to this field
            for d in selected:
                assigned[d] = group_name

        # After attempting to fully protect fields, if we still haven't reached min_protect, assign remaining unassigned drones to protect nearest threatened fields
        if total_protecting_count() < min_protect:
            # Build list of unassigned drones
            unassigned_now = [d for d, g in assigned.items() if g is None]
            # For each unassigned drone, pick the nearest threatened field and assign, until we reach min_protect or run out
            # Prepare field centers
            field_centers = {f.id: center_of(f) for f in threatened}
            # Sort unassigned drones by proximity to any field (closest first)
            def nearest_field_for_drone(d):
                best = None
                best_dist = float("inf")
                for f in threatened:
                    cx, cy = field_centers[f.id]
                    dt = dist_to_point(d, cx, cy)
                    if dt < best_dist:
                        best_dist = dt
                        best = f
                return best, best_dist

            # Sort drones by distance to their nearest field
            unassigned_now.sort(key=lambda d: nearest_field_for_drone(d)[1])
            for d in unassigned_now:
                if total_protecting_count() >= min_protect:
                    break
                nearest_field, _ = nearest_field_for_drone(d)
                if nearest_field is None:
                    continue
                assigned[d] = f"protecting {nearest_field.id}"

        # Finally, everything not assigned to protecting group becomes idle
        for d in drones:
            final_group = assigned[d]
            if final_group is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, final_group)