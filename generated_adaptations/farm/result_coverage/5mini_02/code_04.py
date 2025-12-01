from typing import List, Dict, Set
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between drone and field center
        def distance_to_field(drone, field):
            fx = (field.left + field.right) / 2.0
            fy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0) - fx
            dy = getattr(drone.location, "y", 0) - fy
            return math.hypot(dx, dy)

        idle_group = "idle"
        # gather threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # assign all to idle if no threats
            if idle_group in group_ids:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            return

        # Sort fields by descending threat_level, deterministic tie-break by id
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Prepare pools of components
        comps_list = list(components)  # ensure repeatable ordering
        # Map component to distance for reuse
        dist_cache = {}

        # Utility to get sorted candidates by distance to a given field
        def sorted_by_distance(cands, field):
            # compute/cache
            def key_func(c):
                if c not in dist_cache:
                    dist_cache[c] = distance_to_field(c, field)
                return (dist_cache[c], str(getattr(c, "target_id", "")), id(c))
            return sorted(cands, key=key_func)

        # Validate required group ids exist; build protect group names set for existing fields
        available_protect_groups = {f"id_{getattr(f, 'id', '')}": f"protecting {f.id}" for f in threatened_fields}
        # But we will check actual group_id strings directly when assigning.

        # Step 1: Fully protect the top field (highest threat) with closest drones (mandatory)
        assignments: Dict[str, List] = {}  # field_id -> list of components assigned to protect it
        assigned_set: Set = set()

        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        # If protecting group or idle missing, fallback to safe behavior: assign all to idle
        if top_group not in group_ids or idle_group not in group_ids:
            # fallback assign all to idle
            if idle_group in group_ids:
                for comp in comps_list:
                    environment.assign_group(comp, idle_group)
            return

        needed_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Identify drones already protecting the top field
        already_protecting_top = [c for c in comps_list if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id]

        # Start with those
        selected_top = list(already_protecting_top)

        # If still short, select closest drones from others, preferring idle/moving before displacing other protectors
        if len(selected_top) < needed_top:
            others = [c for c in comps_list if c not in selected_top]
            # Split others into non-protectors and protectors of other fields
            non_protectors = [c for c in others if getattr(c, "state", None) != "protecting"]
            protectors_other = [c for c in others if getattr(c, "state", None) == "protecting"]
            # sort by distance
            non_protectors_sorted = sorted_by_distance(non_protectors, top_field)
            protectors_other_sorted = sorted_by_distance(protectors_other, top_field)
            for c in non_protectors_sorted:
                if len(selected_top) >= needed_top:
                    break
                selected_top.append(c)
            for c in protectors_other_sorted:
                if len(selected_top) >= needed_top:
                    break
                selected_top.append(c)

        # Cap selected to needed_top
        selected_top = selected_top[:needed_top]
        assignments[top_field.id] = selected_top
        assigned_set.update(selected_top)

        # Step 2: Try to fully protect other fields in descending threat order using remaining drones
        remaining_comps = [c for c in comps_list if c not in assigned_set]

        for field in threatened_fields[1:]:
            protect_group = f"protecting {field.id}"
            # only consider if protecting group exists
            if protect_group not in group_ids:
                continue
            needed = int(getattr(field, "drones_for_full_protection", 0))
            if needed <= 0:
                continue
            # Count already protecting this field among remaining comps (we have not assigned those yet)
            already = [c for c in remaining_comps if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id]
            selected = list(already)
            if len(selected) < needed:
                # choose additional drones from remaining_comps excluding already
                pool = [c for c in remaining_comps if c not in selected]
                # prefer non-protectors first
                non_protectors = [c for c in pool if getattr(c, "state", None) != "protecting"]
                protectors_other = [c for c in pool if getattr(c, "state", None) == "protecting"]
                non_protectors_sorted = sorted_by_distance(non_protectors, field)
                protectors_other_sorted = sorted_by_distance(protectors_other, field)
                for c in non_protectors_sorted:
                    if len(selected) >= needed:
                        break
                    selected.append(c)
                for c in protectors_other_sorted:
                    if len(selected) >= needed:
                        break
                    selected.append(c)
            # If after selection we have enough to fully protect, commit them
            if len(selected) >= needed:
                selected = selected[:needed]
                assignments[field.id] = selected
                for c in selected:
                    if c in remaining_comps:
                        remaining_comps.remove(c)
                    assigned_set.add(c)
            # else do not partially commit at this step (we will consider partial later)
            # proceed to next field

        # Step 3: If there are leftover drones and none can be fully protected further, assign remaining drones
        # to the highest remaining threat field for partial protection (if any)
        remaining_comps = [c for c in comps_list if c not in assigned_set]
        if remaining_comps:
            # find highest-threat field among remaining (could be top_field if extra drones remain, but top_field already handled)
            # Exclude fields already fully assigned
            remaining_fields = [f for f in threatened_fields if f.id not in assignments]
            if remaining_fields:
                target_field = remaining_fields[0]  # highest remaining threat
                target_group = f"protecting {target_field.id}"
                if target_group in group_ids:
                    # Assign all remaining drones to this field as partial protection
                    # Prefer drones closest to this field
                    rem_sorted = sorted_by_distance(remaining_comps, target_field)
                    assignments[target_field.id] = rem_sorted
                    for c in rem_sorted:
                        assigned_set.add(c)
                    remaining_comps = []

        # Finally, assign groups: drones in assignments go to their respective protecting groups; all others -> idle
        # Ensure idle_group exists
        if idle_group not in group_ids:
            # If idle not available, assign everyone to protecting groups that exist (best-effort)
            for field_id, comps in assignments.items():
                grp = f"protecting {field_id}"
                for c in comps:
                    if grp in group_ids:
                        environment.assign_group(c, grp)
            return

        # Assign protecting groups
        for field_id, comps_assigned in assignments.items():
            grp = f"protecting {field_id}"
            # Only assign if group exists
            if grp not in group_ids:
                continue
            for c in comps_assigned:
                environment.assign_group(c, grp)

        # Assign remaining drones to idle
        for c in comps_list:
            if c not in assigned_set:
                environment.assign_group(c, idle_group)