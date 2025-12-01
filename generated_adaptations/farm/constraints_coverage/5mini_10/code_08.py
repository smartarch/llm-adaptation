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
            Always returns at most `required` drones and removes them from available_set.
            """
            selected = []

            # helper to pop drone from available_set if present
            def take(drone):
                if drone in available_set:
                    available_set.remove(drone)
                selected.append(drone)

            if required <= 0:
                return selected

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
        # Ensure non-negative
        req_high = max(0, req_high)
        selected_high = select_drones_for_field(highest_field, available, req_high)
        assigned_for_field[highest_field.id] = selected_high

        # 2) For other fields, compute efficiency score and try to allocate greedily (respect capacity)
        other_fields = threatened_fields[1:]
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

        for score, field in scored_fields:
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                assigned_for_field[field.id] = []
                continue
            req = int(getattr(field, "drones_for_full_protection", 0))
            req = max(0, req)
            # If enough available to fully protect, do so; else skip (we will consider partial filling later up to capacity)
            if len(available) >= req and req > 0:
                sel = select_drones_for_field(field, available, req)
                assigned_for_field[field.id] = sel
            else:
                assigned_for_field[field.id] = []

        # 3) If there are drones left, assign them to the single best remaining field (highest score) up to its remaining capacity
        if available:
            # Build candidates: fields with valid group and remaining capacity >0
            candidates = []
            for _, f in scored_fields:
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    continue
                req = int(getattr(f, "drones_for_full_protection", 0))
                req = max(0, req)
                already = len(assigned_for_field.get(f.id, []))
                remaining_capacity = max(0, req - already)
                # if field had req==0, treat capacity as 0 (can't meaningfully assign)
                if remaining_capacity > 0:
                    score = getattr(f, "threat_level", 0.0) / (req if req > 0 else 1)
                    candidates.append((score, f, remaining_capacity))
            # Also consider fields that were not in scored_fields (unlikely) and highest_field if it has remaining capacity (edge cases)
            # Check highest field remaining capacity too (should be zero normally)
            high_req = int(getattr(highest_field, "drones_for_full_protection", 0))
            high_req = max(0, high_req)
            high_already = len(assigned_for_field.get(highest_field.id, []))
            high_rem = max(0, high_req - high_already)
            if high_rem > 0:
                # include highest field candidate with its efficiency score
                score_high = getattr(highest_field, "threat_level", 0.0) / (high_req if high_req > 0 else 1)
                candidates.append((score_high, highest_field, high_rem))

            if candidates:
                # pick best by score then threat
                candidates.sort(key=lambda x: (x[0], getattr(x[1], "threat_level", 0.0)), reverse=True)
                best_score, best_field, best_capacity = candidates[0]
                # select up to best_capacity but not exceed number of available drones
                to_take = min(best_capacity, len(available))
                sel_partial = select_drones_for_field(best_field, available, to_take)
                assigned_for_field.setdefault(best_field.id, [])
                # Ensure we don't exceed capacity (defensive)
                current_assigned = len(assigned_for_field[best_field.id])
                can_append = max(0, int(getattr(best_field, "drones_for_full_protection", 0)) - current_assigned)
                if sel_partial:
                    assigned_for_field[best_field.id].extend(sel_partial[:can_append])

        # 4) Explicitly assign selected protecting drones to their groups
        selected_set = set()
        for fid, drones in assigned_for_field.items():
            group_name = f"protecting {fid}"
            if group_name not in group_ids:
                continue
            # Enforce cap: do not assign more than drones_for_full_protection
            cap = max(0, int(getattr(next((f for f in environment.fields if f.id == fid), None), "drones_for_full_protection", len(drones))))
            cap = max(0, cap)
            # Assign up to cap drones from the list
            for d in drones[:cap]:
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