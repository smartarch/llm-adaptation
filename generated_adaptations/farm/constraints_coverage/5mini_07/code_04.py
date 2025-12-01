from math import ceil, hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        def assign(c, gid):
            environment.assign_group(c, gid)

        drones = list(components)
        total_drones = len(drones)
        min_protect = int(ceil(total_drones / 2.0))

        # Fields with positive threat
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not candidate_fields:
            for c in drones:
                assign(c, "idle")
            return

        # Select highest-threat field (tie-breaker: first)
        highest = max(candidate_fields, key=lambda f: f.threat_level)

        # Helper: field center
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Helper: distance from a drone to field center
        def dist_to_field(c, fx, fy):
            return hypot(c.location.x - fx, c.location.y - fy)

        # Required drones for a field (ceil)
        def required_for(f):
            return int(ceil(getattr(f, "drones_for_full_protection", 0)))

        # Keep track of assignments: drone -> field_id (strings)
        assigned = {}  # c -> field.id

        # Available drones list (start with all)
        available = list(drones)

        # Function to get current protectors for a specific field (based on observed state)
        def current_protectors_for_field(field):
            return [c for c in drones if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id]

        # 1) Ensure highest-threat field is fully protected
        fx, fy = field_center(highest)
        req = required_for(highest)
        # Collect current protectors currently protecting highest
        current_high = current_protectors_for_field(highest)
        # Assign those (they may be fewer than required)
        for c in current_high:
            assigned[c] = highest.id
            if c in available:
                available.remove(c)

        # If more are needed, pick closest from available
        if len(current_high) < req:
            # sort available by distance to highest
            available_sorted = sorted(available, key=lambda c: dist_to_field(c, fx, fy))
            needed = req - len(current_high)
            for c in available_sorted[:needed]:
                assigned[c] = highest.id
                available.remove(c)

        # 2) Try to fully protect other fields by priority (threat desc)
        other_fields = [f for f in candidate_fields if f.id != highest.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for f in other_fields:
            if not available:
                break
            fx, fy = field_center(f)
            req_f = required_for(f)
            # Count current protectors for this field
            current_f = current_protectors_for_field(f)
            # Add current protectors (if not already assigned)
            for c in current_f:
                if c not in assigned:
                    assigned[c] = f.id
                    if c in available:
                        available.remove(c)
            current_count = sum(1 for c in assigned if assigned.get(c) == f.id)
            if current_count >= req_f:
                continue
            need = req_f - current_count
            # Select closest available drones to this field
            available_sorted = sorted(available, key=lambda c: dist_to_field(c, fx, fy))
            to_take = available_sorted[:need]
            for c in to_take:
                assigned[c] = f.id
                available.remove(c)

        # 3) If we still have fewer than min_protect drones assigned to protection,
        #    and there are threatened fields and available drones, assign extra drones to the best field
        assigned_count = len(assigned)
        if assigned_count < min_protect and available:
            # Choose the best field to receive extra drones: highest threat (could be highest or next best)
            best_field = max(candidate_fields, key=lambda f: f.threat_level)
            fx, fy = field_center(best_field)
            # Sort remaining available drones by proximity to that field
            available_sorted = sorted(available, key=lambda c: dist_to_field(c, fx, fy))
            need_extra = min(len(available_sorted), min_protect - assigned_count)
            for c in available_sorted[:need_extra]:
                # assign these even if it creates partial protection
                assigned[c] = best_field.id
                available.remove(c)

        # Final assignment: assigned -> protecting {field.id}, others -> idle
        for c in drones:
            if c in assigned:
                group_name = f"protecting {assigned[c]}"
                assign(c, group_name)
            else:
                assign(c, "idle")