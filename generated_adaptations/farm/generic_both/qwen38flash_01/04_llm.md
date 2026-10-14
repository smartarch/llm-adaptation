

## Strategy Description

The fix is straightforward: the base class `FarmAdaptation` was not imported. The error message clearly states `NameError: name 'FarmAdaptation' is not defined`. I need to add the proper import statement at the top of the file, importing `FarmAdaptation` from `generated_adaptations.base_classes.farm`.

The rest of the strategy remains unchanged:
- Fields sorted by threat level (descending) get prioritized for full protection.
- Closest available drones are assigned to the highest-threat field first.
- Drones already protecting a needed field are kept in place (stability).
- No field is overprotected beyond `drones_for_full_protection`.
- Surplus/idle drones are redistributed to keep at least half active.
- Partial protection is used as a last resort, preferring full protection of fewer fields.

## Code Implementation

```python
import math
from typing import List, Dict, Set

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that:
    - Always fully protects the most threatened field with closest drones.
    - Greedily fully protects subsequent fields in threat order.
    - Minimizes unnecessary drone reassignments for stability.
    - Avoids overprotection.
    - Keeps drones productive (minimizes idle).
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # --- Helper: find the group name for protecting a given field ---
        def field_group_name(field) -> str:
            """Find the group ID that corresponds to protecting `field`."""
            for gid in group_ids:
                if gid == "idle":
                    continue
                if str(field.id) == gid:
                    return gid
                if f"protecting_{field.id}" == gid:
                    return gid
                if f"protect_{field.id}" == gid:
                    return gid
                if gid.startswith("protect") and str(field.id) in gid:
                    return gid
            return "idle"

        # --- Helper: Euclidean distance from drone to field center ---
        def drone_field_dist(drone, field) -> float:
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return math.sqrt(dx * dx + dy * dy)

        # --- Step 0: Gather active fields sorted by threat (descending) ---
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # If no active fields, park everyone idle
        if not active_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # --- Step 1: Determine each drone's current field target ---
        current_target: Dict[int, str] = {}
        for drone in components:
            tgt = getattr(drone, 'target_id', None)
            if tgt is not None and tgt != "" and tgt != "idle":
                current_target[id(drone)] = str(tgt)
            else:
                current_target[id(drone)] = None

        # --- Step 2: Count how many drones each field currently has ---
        field_id_set = {str(f.id) for f in active_fields}
        field_current_count: Dict[str, int] = {str(f.id): 0 for f in active_fields}
        for d_id, tgt in current_target.items():
            if tgt in field_id_set:
                field_current_count[tgt] += 1

        # --- Step 3: Determine how many drones each field NEEDS ---
        field_need: Dict[str, int] = {}
        for f in active_fields:
            fid = str(f.id)
            field_need[fid] = f.drones_for_full_protection

        # --- Step 4: Build the assignment ---
        assigned: Set[int] = set()
        field_assignments: Dict[str, List[int]] = {str(f.id): [] for f in active_fields}
        drone_to_field: Dict[int, str] = {}

        # First pass: keep drones on fields that still need them (stability)
        for f in active_fields:
            fid = str(f.id)
            keep_capacity = field_need[fid]
            for drone in components:
                d_id = id(drone)
                if d_id in assigned:
                    continue
                if current_target.get(d_id) == fid:
                    if len(field_assignments[fid]) < keep_capacity:
                        field_assignments[fid].append(d_id)
                        drone_to_field[d_id] = fid
                        assigned.add(d_id)

        # Second pass: fill remaining slots with closest unassigned drones
        unassigned_drones = [d for d in components if id(d) not in assigned]

        for f in active_fields:
            fid = str(f.id)
            remaining_slots = field_need[fid] - len(field_assignments[fid])
            if remaining_slots <= 0:
                continue
            candidates = sorted(unassigned_drones, key=lambda d: drone_field_dist(d, f))
            for d in candidates:
                if id(d) in assigned:
                    continue
                field_assignments[fid].append(id(d))
                drone_to_field[id(d)] = fid
                assigned.add(id(d))
                remaining_slots -= 1
                if remaining_slots <= 0:
                    break

        # Third pass: handle surplus drones on overprotected fields
        for f in active_fields:
            fid = str(f.id)
            while len(field_assignments[fid]) > field_need[fid]:
                excess_id = field_assignments[fid].pop()
                assigned.discard(excess_id)
                drone_to_field.pop(excess_id, None)

        # Fourth pass: remaining unassigned drones → assign to fields
        leftover = [d for d in components if id(d) not in assigned]
        if leftover:
            for f in active_fields:
                if not leftover:
                    break
                fid = str(f.id)
                current_in_field = len(field_assignments[fid])
                if current_in_field >= field_need[fid]:
                    continue
                slots_to_fill = field_need[fid] - current_in_field
                for d in list(leftover):
                    if slots_to_fill <= 0:
                        break
                    field_assignments[fid].append(id(d))
                    drone_to_field[id(d)] = fid
                    assigned.add(id(d))
                    leftover.remove(d)
                    slots_to_fill -= 1

            if leftover and active_fields:
                top_field = active_fields[0]
                for d in leftover:
                    field_assignments[str(top_field.id)].append(id(d))
                    drone_to_field[id(d)] = str(top_field.id)
                    assigned.add(id(d))

        # --- Step 5: Ensure at least half the drones are active ---
        total_drones = len(components)
        active_count = sum(len(v) for v in field_assignments.values())
        if active_count < total_drones // 2 and active_fields:
            idle_drones = [d for d in components if id(d) not in assigned]
            for f in active_fields:
                if not idle_drones:
                    break
                fid = str(f.id)
                for d in list(idle_drones):
                    field_assignments[fid].append(id(d))
                    drone_to_field[id(d)] = fid
                    assigned.add(id(d))
                    idle_drones.remove(d)
                    active_count += 1
                    if active_count >= total_drones // 2:
                        break
                if active_count >= total_drones // 2:
                    break

        # --- Step 6: Make final assignments ---
        for drone in components:
            d_id = id(drone)
            if d_id in drone_to_field:
                fid = drone_to_field[d_id]
                field_obj = next((f for f in environment.fields if str(f.id) == fid), None)
                if field_obj is not None:
                    gname = field_group_name(field_obj)
                    environment.assign_group(drone, gname)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
```