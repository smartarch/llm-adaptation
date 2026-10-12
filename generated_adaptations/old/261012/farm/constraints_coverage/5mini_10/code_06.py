import math
from math import ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper functions
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        def select_drones_for_field(field, available_set, required):
            """
            Select up to `required` drones from available_set for `field`.
            Preference order:
              1) currently protecting this field
              2) moving_to_field with target this field
              3) idle drones (closest first)
              4) other drones (closest first)
            Returns list of selected drones (may be fewer than required if not enough available).
            """
            selected = []

            # helper to pop drone from available_set if present
            def take(drone):
                if drone in available_set:
                    available_set.remove(drone)
                selected.append(drone)

            # 1) already protecting this field
            for c in list(available_set):
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                    take(c)
                    if len(selected) >= required:
                        return selected

            # 2) moving to this field
            for c in list(available_set):
                if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == field.id:
                    take(c)
                    if len(selected) >= required:
                        return selected

            # 3) idle drones, closest first
            idle_list = [c for c in available_set if getattr(c, "state", None) == "idle"]
            idle_list.sort(key=lambda c: distance_to_field_center(c, field))
            for c in idle_list:
                take(c)
                if len(selected) >= required:
                    return selected

            # 4) remaining drones sorted by distance
            rem = list(available_set)
            rem.sort(key=lambda c: distance_to_field_center(c, field))
            for c in rem:
                take(c)
                if len(selected) >= required:
                    return selected

            return selected

        idle_group = "idle"
        all_drones = list(components)
        total_drones = len(all_drones)

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields -> assign all to idle/fallback and return
        if not threatened_fields:
            if idle_group in group_ids:
                for c in all_drones:
                    environment.assign_group(c, idle_group)
            else:
                fallback = group_ids[0] if group_ids else None
                for c in all_drones:
                    if fallback:
                        environment.assign_group(c, fallback)
            return

        # Sort by threat_level desc to pick the mandatory highest-threat field
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        highest_field = threatened_fields[0]
        highest_group = f"protecting {highest_field.id}"
        # If protecting group for highest field missing, cannot follow strategy -> fall back to idle assignment
        if highest_group not in group_ids:
            if idle_group in group_ids:
                for c in all_drones:
                    environment.assign_group(c, idle_group)
            else:
                fallback = group_ids[0] if group_ids else None
                for c in all_drones:
                    if fallback:
                        environment.assign_group(c, fallback)
            return

        # Available pool of drones to allocate
        available = set(all_drones)
        assigned_for_field = {}  # field.id -> list of drones assigned

        # 1) Fully protect the highest field (mandatory)
        req_high = int(getattr(highest_field, "drones_for_full_protection", 0))
        selected_high = select_drones_for_field(highest_field, available, req_high)
        # If for some weird reason we couldn't find enough (e.g., not enough drones total),
        # selected_high will be fewer; still assign whatever we have.
        assigned_for_field[highest_field.id] = selected_high

        # 2) For other fields, compute efficiency score and try to allocate greedily
        other_fields = threatened_fields[1:]
        # Score: threat_level per drone (higher is better). Use drones_for_full_protection >=1.
        scored_fields = []
        for f in other_fields:
            drones_needed = int(getattr(f, "drones_for_full_protection", 0))
            if drones_needed <= 0:
                score = getattr(f, "threat_level", 0.0)
            else:
                score = getattr(f, "threat_level", 0.0) / drones_needed
            scored_fields.append((score, f))
        # Sort by score desc, tie-breaker threat_level desc
        scored_fields.sort(key=lambda sf: (sf[0], getattr(sf[1], "threat_level", 0.0)), reverse=True)

        # Try to fully protect as many high-efficiency fields as possible
        for score, field in scored_fields:
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            req = int(getattr(field, "drones_for_full_protection", 0))
            if req <= 0:
                # nothing to allocate, skip
                assigned_for_field[field.id] = []
                continue
            # If not enough drones remain to fully protect and we have other fields with better score, skip full protection attempt
            # But here we greedily try to fully protect if we can (req <= len(available))
            if len(available) >= req:
                sel = select_drones_for_field(field, available, req)
                assigned_for_field[field.id] = sel
            else:
                # Not enough to fully protect this field; we will consider partial allocations later.
                assigned_for_field[field.id] = []

        # 3) If there are drones left, assign them to the single best remaining field (highest score) as partial protection
        # Determine which field (among remaining with threat>0) has highest score and a valid group.
        leftover = list(available)
        if leftover:
            # find candidates: fields that either haven't been fully satisfied (assigned_for_field[f.id] < required)
            candidates = []
            for f in other_fields:
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    continue
                req = int(getattr(f, "drones_for_full_protection", 0))
                current_assigned = len(assigned_for_field.get(f.id, []))
                # compute score same as above
                drones_needed = req if req > 0 else 1
                score = getattr(f, "threat_level", 0.0) / drones_needed
                candidates.append((score, f, req, current_assigned))
            # Choose best by score
            if candidates:
                candidates.sort(key=lambda x: (x[0], getattr(x[1], "threat_level", 0.0)), reverse=True)
                best = candidates[0][1]
                best_group = f"protecting {best.id}"
                # Fill remaining available drones to this best field (even if partial)
                # select up to all available
                sel_partial = select_drones_for_field(best, available, len(available))
                # append to any existing assigned for that field
                assigned_for_field.setdefault(best.id, [])
                assigned_for_field[best.id].extend(sel_partial)

        # 4) Explicitly assign selected protecting drones to their groups
        selected_set = set()
        for fid, drones in assigned_for_field.items():
            group_name = f"protecting {fid}"
            if group_name not in group_ids:
                continue
            for d in drones:
                environment.assign_group(d, group_name)
                selected_set.add(d)

        # 5) All others -> idle (or fallback)
        if idle_group in group_ids:
            for d in all_drones:
                if d not in selected_set:
                    environment.assign_group(d, idle_group)
        else:
            fallback = group_ids[0] if group_ids else None
            for d in all_drones:
                if d not in selected_set and fallback:
                    environment.assign_group(d, fallback)