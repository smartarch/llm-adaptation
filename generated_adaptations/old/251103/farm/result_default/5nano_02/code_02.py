from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: get field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: squared distance from drone to a point (tx, ty)
        def drone_dist2_to(drone, tx, ty):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", None)
            if x is None:
                if isinstance(loc, dict):
                    x = loc.get("x", 0.0)
                else:
                    x = 0.0
            y = getattr(loc, "y", None)
            if y is None:
                if isinstance(loc, dict):
                    y = loc.get("y", 0.0)
                else:
                    y = 0.0
            dx = x - tx
            dy = y - ty
            return dx * dx + dy * dy

        # Determine top field (highest threat_level > 0)
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        top_field = None
        if threat_fields:
            # pick the field with the maximum threat_level; in tie, pick the first
            top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # If no threat, idle all drones
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Compute current protection counts from existing assignments
        # Counts per field id
        counts = {}
        for f in environment.fields:
            if getattr(f, "threat_level", 0) > 0:
                counts[f.id] = 0

        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    counts[tid] = counts.get(tid, 0) + 1

        # Current protection for top field
        current_top = counts.get(top_field.id, 0)

        # Drones needed to fully protect top field
        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top)

        # Allocate to top field: closest drones not already protecting it
        # Prepare a sorted list by distance to top field center
        tx, ty = field_center(top_field)
        drones_sorted = sorted(components, key=lambda d: drone_dist2_to(d, tx, ty))

        assigned = set()
        # First, assign needed_top drones to top_field
        remaining_top = needed_top
        for d in drones_sorted:
            if remaining_top <= 0:
                break
            # Skip drones already protecting top_field
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                continue
            environment.assign_group(d, f"protecting {top_field.id}")
            assigned.add(d)
            # Update counts to reflect reassignment
            old_id = getattr(d, "target_id", None)
            if old_id is not None and old_id != top_field.id:
                counts[old_id] = max(0, counts.get(old_id, 0) - 1)
            counts[top_field.id] = counts.get(top_field.id, 0) + 1
            remaining_top -= 1

        # After top field allocation, determine available drones for others
        available = [d for d in components if d not in assigned and not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id)]

        # Sort other fields by threat level (desc)
        other_fields = [f for f in threat_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # For each other field, attempt to fill up to its full protection
        for field in other_fields:
            if not available:
                break
            cur = counts.get(field.id, 0)
            need = max(0, getattr(field, "drones_for_full_protection", 0) - cur)
            if need <= 0:
                continue

            # Sort available drones by distance to this field
            fx, fy = field_center(field)
            available.sort(key=lambda d: drone_dist2_to(d, fx, fy))

            take = min(need, len(available))
            for i in range(take):
                d = available.pop(0)
                environment.assign_group(d, f"protecting {field.id}")
                assigned.add(d)
                counts[field.id] = counts.get(field.id, 0) + 1
            # continue to next field

        # Finally, assign any remaining drones to idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")