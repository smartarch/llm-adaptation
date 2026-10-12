Reasoning and improved adaptation strategy

Goal:
- Continue to satisfy the core rule: always fully protect the field with the highest threat level using the closest drones. If that field is already fully protected, keep those drones there. Otherwise, allocate drones to top fields in a way that minimizes churn and travel time, while preserving protection on already-threatened fields when possible.

What’s new in this approach:
- Multi-field, threat-ordered allocation with non-destructive policy:
  - We allocate drones to fields in threat order, but we never steal drones from higher-priority fields to protect lower-priority ones.
  - For each field, we use the drones already targeting that field as a starting point (reservation). If more are needed, we pull in the closest idle drones. If there aren’t idle drones, we try to allocate from drones not yet allocated to any field, minimizing travel distance.
  - After filling all threatened fields as much as possible, drones not allocated to any field are either kept protecting their current threatened field (to avoid churn) or set to idle if not protecting any threatened field.
- This balances guarding the top field first while still offering opportunistic help to other fields without causing excessive churn.

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
        fields_sorted = sorted(
            threat_fields,
            key=lambda f: getattr(f, "threat_level", 0),
            reverse=True
        )

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_point(drone, point):
            dx = getattr(drone.location, "x", 0.0) - point[0]
            dy = getattr(drone.location, "y", 0.0) - point[1]
            return math.hypot(dx, dy)

        # Top-threat field (highest priority)
        top_field = fields_sorted[0]
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
        centers = {fld.id: field_center(fld) for fld in fields_sorted}
        allocated_to_field = {fld.id: [] for fld in fields_sorted}

        allocated_to_field[top_field_id] = list(assigned_to_top)

        # Idle pool for other fields
        idle_pool = [d for d in components if d not in assigned_to_top and getattr(d, "target_id", None) is None]

        # For each other threatened field, fill deficits with closest idle drones
        for fld in fields_sorted[1:]:
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
                # Preserve protection for drones already protecting a threatened field (to minimize churn)
                tid = getattr(d, "target_id", None)
                threatened_ids = {fld.id for fld in fields_sorted}
                if tid in threatened_ids:
                    environment.assign_group(d, f"protecting {tid}")
                else:
                    environment.assign_group(d, "idle")
```