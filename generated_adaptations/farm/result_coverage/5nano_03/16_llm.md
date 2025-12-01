Reasoning and improved adaptation strategy

Goal recap:
- The core rule remains: always fully protect the field with the highest threat level using the closest drones. If that field is already fully protected, keep those drones there. Any remaining drones can be idle or used for other fields, but the top-field protection must not be sacrificed.
- A robust strategy now balances top-field protection with opportunistic help to other threatened fields only after the top field is fully protected, using idle drones (to minimize churn). Drones already targeting the top field are treated as reserved for that field. Drones protecting other fields are preserved unless needed to fill the top field.
- After top-field protection is achieved, we attempt to reduce further damage by lightly assisting other threatened fields in threat-order using closest idle drones.

Core ideas:
- Reserve drones heading to the top field (target_id == top_field.id or state == moving_to_field toward that id) and keep them for the top field until it is fully protected.
- If there are not enough reserved drones, pull in the closest idle drones to complete the top-field protection (no churn from already-protecting drones for other fields).
- Once the top field is fully protected, allocate idle drones to other threatened fields in threat-order, again using distance to the field center to minimize travel time.
- Drones that are currently protecting other fields remain in their current protection if there are no idle drones to reallocate; only allocate idle drones to fill deficits of other fields.

Python implementation:

```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: getattr(f, "threat_level", 0),
            reverse=True
        )

        # Helper: field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance from a drone to a point
        def dist_to_point(drone, point):
            dx = getattr(drone.location, "x", 0.0) - point[0]
            dy = getattr(drone.location, "y", 0.0) - point[1]
            return math.hypot(dx, dy)

        # Top-threat field
        top_field = threat_fields_sorted[0]
        top_field_id = top_field.id
        top_center = field_center(top_field)
        needed_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones reserved for top field: target_id == top_field_id OR moving_to_field toward it
        reserved_top = []
        for d in components:
            tid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            if tid == top_field_id or (st == "moving_to_field" and tid == top_field_id):
                reserved_top.append(d)

        # Decide which drones go to top field
        assigned_to_top = []
        if len(reserved_top) >= needed_top:
            assigned_to_top = reserved_top[:needed_top]
        else:
            assigned_to_top = list(reserved_top)
            remaining = needed_top - len(assigned_to_top)
            if remaining > 0:
                pool = [d for d in components if d not in assigned_to_top and getattr(d, "target_id", None) is None]
                pool.sort(key=lambda d: dist_to_point(d, top_center))
                assigned_to_top.extend(pool[:remaining])

        # After top is filled, allocate idle drones to other threatened fields in threat order
        centers = {fld.id: field_center(fld) for fld in threat_fields_sorted}
        allocated_to_field = {fld.id: [] for fld in threat_fields_sorted}

        # Top field allocation
        allocated_to_field[top_field_id] = list(assigned_to_top)

        # Idle pool for other fields
        idle_pool = [d for d in components if d not in assigned_to_top and getattr(d, "target_id", None) is None]

        # For each other threatened field, fill deficits with closest idle drones
        for fld in threat_fields_sorted[1:]:
            need = int(getattr(fld, "drones_for_full_protection", 0))
            if need <= 0:
                continue
            current = [d for d in components if getattr(d, "target_id", None) == fld.id]
            deficit = max(0, need - len(current))
            if deficit <= 0:
                continue
            center = centers[fld.id]
            idle_pool.sort(key=lambda d: dist_to_point(d, center))
            take = min(deficit, len(idle_pool))
            if take > 0:
                chosen = idle_pool[:take]
                idle_pool = idle_pool[take:]
                allocated_to_field[fld.id].extend(chosen)

        # Build final mapping: drone -> field_id
        drone_to_field = {}
        for fid, lst in allocated_to_field.items():
            for d in lst:
                drone_to_field[d] = fid

        # Assign groups
        for d in components:
            if d in drone_to_field:
                environment.assign_group(d, f"protecting {drone_to_field[d]}")
            else:
                # If drone is currently protecting a threatened field, keep it with that field
                tid = getattr(d, "target_id", None)
                threatened_ids = {fld.id for fld in threat_fields_sorted}
                if tid in threatened_ids:
                    environment.assign_group(d, f"protecting {tid}")
                else:
                    environment.assign_group(d, "idle")
```