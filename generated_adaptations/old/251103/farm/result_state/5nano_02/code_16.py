from typing import List

# Assuming the base class is importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper: field center
        field_by_id = {f.id: f for f in threatened_fields}
        centers = {}
        for f in threatened_fields:
            centers[f.id] = (
                (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0,
                (getattr(f, "top", 0)  + getattr(f, "bottom", 0)) / 2.0,
            )

        # Compute current protection counts (protecting) and arriving counts (moving_to_field)
        protecting = {f.id: 0 for f in threatened_fields}
        arriving = {f.id: 0 for f in threatened_fields}
        # Also try to include arriving_drones on the field if present
        for d in components:
            s = getattr(d, "state", None)
            t = getattr(d, "target_id", None)
            if s == "protecting" and t in protecting:
                protecting[t] += 1
            elif s == "moving_to_field" and t in arriving:
                arriving[t] += 1
        # Some environments expose arriving_drones on the field; include if present
        for f in threatened_fields:
            arr = getattr(f, "arriving_drones", 0)
            if isinstance(arr, (int, float)):
                arriving[f.id] += int(arr)

        # Step 1: Allocate for the top field (highest threat) to full protection
        top_field = threatened_fields[0]
        top_current = protecting.get(top_field.id, 0) + arriving.get(top_field.id, 0)
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        top_needed = max(0, top_required - top_current)

        assigned_to_protect = set()

        if top_needed > 0:
            cx, cy = centers[top_field.id]
            candidates = []
            for d in components:
                # Skip drones already protecting the top field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                # Do not displace drones currently protecting other fields
                if getattr(d, "state", None) == "protecting":
                    continue
                # Optional: allow reassigning drones en route to other fields (only if beneficial)
                # We will allow, except we keep note to avoid endless churn by assigning only when needed.
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))

            candidates.sort(key=lambda x: x[0])
            for dist, drone in candidates:
                if top_needed <= 0:
                    break
                environment.assign_group(drone, f"protecting {top_field.id}")
                assigned_to_protect.add(drone)
                top_needed -= 1

        # Step 2: Recompute counts after top-field enforcement
        protecting = {f.id: 0 for f in threatened_fields}
        arriving = {f.id: 0 for f in threatened_fields}
        for d in components:
            s = getattr(d, "state", None)
            t = getattr(d, "target_id", None)
            if s == "protecting" and t in protecting:
                protecting[t] += 1
            elif s == "moving_to_field" and t in arriving:
                arriving[t] += 1
        for f in threatened_fields:
            arriving[f.id] += getattr(f, "arriving_drones", 0) if isinstance(getattr(f, "arriving_drones", 0), int) else 0

        # Step 3: Allocate remaining drones to other fields in threat order
        # We consider all other fields (in order) and assign any non-protecting drones
        for field in threatened_fields[1:]:
            current = protecting.get(field.id, 0) + arriving.get(field.id, 0)
            required = int(getattr(field, "drones_for_full_protection", 0))
            needed = max(0, required - current)
            if needed <= 0:
                continue

            cx, cy = centers[field.id]
            candidates = []
            for d in components:
                if d in assigned_to_protect:
                    continue
                # Do not disturb drones currently protecting this field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    continue
                # Do not displace drones currently protecting other fields (basic stability)
                if getattr(d, "state", None) == "protecting":
                    continue
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))
            candidates.sort(key=lambda x: x[0])

            for dist, drone in candidates:
                if needed <= 0:
                    break
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_to_protect.add(drone)
                needed -= 1

        # Step 4: Idle drones not assigned to protection
        for d in components:
            if d in assigned_to_protect:
                continue
            if getattr(d, "state", None) == "protecting":
                continue
            environment.assign_group(d, "idle")