import math
from math import ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between drone and field center
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        idle_group = "idle"
        total_drones = len(components)
        min_protect = ceil(total_drones / 2) if total_drones > 0 else 0

        # Threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all to idle (or fallback)
        if not threatened_fields:
            if idle_group in group_ids:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            else:
                fallback = group_ids[0] if group_ids else None
                for comp in components:
                    if fallback:
                        environment.assign_group(comp, fallback)
            return

        # Sort fields by descending threat_level (highest first)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        highest_field = threatened_fields[0]
        highest_group = f"protecting {highest_field.id}"

        # Validate group ids: if highest group's not present, fall back to idle assignment
        if highest_group not in group_ids:
            if idle_group in group_ids:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            else:
                fallback = group_ids[0] if group_ids else None
                for comp in components:
                    if fallback:
                        environment.assign_group(comp, fallback)
            return

        # Keep track of available drones to assign
        all_drones = list(components)
        available = set(all_drones)

        # Mapping field.id -> list of drones selected for that field
        assigned_for_field = {}

        # --- 1) Fully protect the highest field using closest drones ---
        required_high = int(getattr(highest_field, "drones_for_full_protection", 0))

        # Drones already protecting the highest field (keep them)
        existing_on_high = [c for c in all_drones
                            if getattr(c, "state", None) == "protecting"
                            and getattr(c, "target_id", None) == highest_field.id]
        # Select them first
        selected_high = list(existing_on_high)
        for c in selected_high:
            if c in available:
                available.remove(c)

        # If more needed, pick closest from remaining (including those protecting other fields)
        if len(selected_high) < required_high:
            needed = max(0, required_high - len(selected_high))
            remaining_list = list(available)
            remaining_list.sort(key=lambda c: distance_to_field_center(c, highest_field))
            to_take = remaining_list[:needed]
            for c in to_take:
                selected_high.append(c)
                if c in available:
                    available.remove(c)

        assigned_for_field[highest_field.id] = selected_high
        protected_count = len(selected_high)

        # --- 2) Try to reach at least half of drones assigned to protection by using other fields ---
        # Iterate other threatened fields in descending threat, attempt to fully protect them if needed
        for field in threatened_fields[1:]:
            if protected_count >= min_protect:
                break  # already satisfied minimum protection usage

            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue  # can't assign to this field if group missing

            required = int(getattr(field, "drones_for_full_protection", 0))

            # Drones already protecting this field and still available (not taken for highest)
            existing_on_field = [c for c in list(available)
                                 if getattr(c, "state", None) == "protecting"
                                 and getattr(c, "target_id", None) == field.id]

            # Select existing ones first
            selected = list(existing_on_field)
            for c in selected:
                if c in available:
                    available.remove(c)

            # Use additional drones if needed and if we still need to increase overall protection count
            # Note: we don't need to fully protect every field -- just use drones until min_protect reached,
            # but we will respect full protection requirement per field (i.e., assign up to required).
            if len(selected) < required and protected_count < min_protect:
                needed_for_field = required - len(selected)
                # but only pick as many as needed to reach min_protect
                needed_to_reach_min = min_protect - protected_count
                to_pick = min(needed_for_field, needed_to_reach_min)
                # pick closest available drones to this field
                remaining_list = list(available)
                remaining_list.sort(key=lambda c: distance_to_field_center(c, field))
                add = remaining_list[:to_pick]
                for c in add:
                    selected.append(c)
                    if c in available:
                        available.remove(c)

            assigned_for_field[field.id] = selected
            protected_count += len(selected)

        # --- 3) Assign groups: protecting groups for selected drones, idle for the rest ---
        # First, assign all selected protecting drones to their protecting groups explicitly
        # (ensuring every component is explicitly re-assigned)
        selected_set = set()
        for fid, drones in assigned_for_field.items():
            group_name = f"protecting {fid}"
            # ensure group exists; skip otherwise (should be present for fields with threat>0 normally)
            if group_name not in group_ids:
                continue
            for c in drones:
                environment.assign_group(c, group_name)
                selected_set.add(c)

        # All remaining drones -> idle (or fallback)
        if idle_group in group_ids:
            for c in all_drones:
                if c not in selected_set:
                    environment.assign_group(c, idle_group)
        else:
            fallback = group_ids[0] if group_ids else None
            for c in all_drones:
                if c not in selected_set and fallback:
                    environment.assign_group(c, fallback)