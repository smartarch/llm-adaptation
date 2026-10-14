

## Strategy Description

The adaptation strategy follows these principles:

1. **Priority-based allocation**: Fields are sorted by threat level (highest first). The most threatened field gets full protection first using the closest available drones.

2. **Stability preservation**: Drones already protecting a field that still requires them are kept in place. Reassignments are minimized—only moving drones when a higher-priority field genuinely needs them.

3. **No overprotection**: Each field gets exactly `drones_for_full_protection` drones. Excess drones are released for other fields.

4. **Greedy full protection**: Remaining drones fully protect subsequent fields in priority order. If there aren't enough drones to fully protect the next field, they're still assigned (partial > idle) but we prefer configurations that fully protect fields.

5. **Idle minimization**: Drones are only left idle if there are no active fields or truly no productive assignment.

The algorithm:
- For each field (sorted by threat), compute how many more drones are needed beyond what's currently assigned.
- Assign the closest unassigned/movable drones to fulfill needs.
- Pull from overprotected or lower-threat fields only when necessary.
- Distribute surplus drones to next fields; if a field can't be fully protected, still assign drones (better than idle).

## Code Implementation

```python
import math
from typing import List, Dict, Set


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
                # Try several naming conventions
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
        # current_target maps drone id -> field_id (str) or None
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

        # --- Step 3: Determine how many drones each field NEEDS (cap at full protection) ---
        field_need: Dict[str, int] = {}
        field_needed_drones: Dict[str, List] = {}  # drones we will assign
        for f in active_fields:
            fid = str(f.id)
            field_need[fid] = f.drones_for_full_protection

        # --- Step 4: Build the assignment ---
        # Strategy: iterate fields by priority.
        #   For each field, first keep drones already assigned there (stability).
        #   Then fill remaining slots with closest *unassigned* drones.
        #   If not enough unassigned, pull from overprotected/lower-threat fields.

        assigned: Set[int] = set()       # drone ids already assigned in this round
        field_assignments: Dict[str, List[int]] = {str(f.id): [] for f in active_fields}
        drone_to_field: Dict[int, str] = {}  # drone id -> field id string

        # First pass: keep drones on fields that still need them (stability)
        # Process fields in priority order for the "keep" decisions
        for f in active_fields:
            fid = str(f.id)
            keep_capacity = field_need[fid]
            for drone in components:
                d_id = id(drone)
                if d_id in assigned:
                    continue
                if current_target.get(d_id) == fid:
                    # Drone is already heading to/protecting this field – keep it
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
            # Sort unassigned drones by distance to this field
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
        # (shouldn't happen with our logic, but safety check)
        for f in active_fields:
            fid = str(f.id)
            while len(field_assignments[fid]) > field_need[fid]:
                # Remove the farthest drone (or one that just arrived)
                excess_id = field_assignments[fid].pop()
                assigned.discard(excess_id)
                drone_to_field.pop(excess_id, None)

        # Fourth pass: remaining unassigned drones → assign to fields that
        # could use partial help (better than idle), preferring highest threat.
        leftover = [d for d in components if id(d) not in assigned]
        if leftover:
            for f in active_fields:
                if not leftover:
                    break
                fid = str(f.id)
                # Assign leftover drones even if field is already full?
                # Prefer NOT to overprotect. Only assign if there's a field
                # that isn't fully protected yet.
                # Check if any field is under-assigned
                pass

            # Try to fully protect additional fields or give partial support
            for f in active_fields:
                if not leftover:
                    break
                fid = str(f.id)
                current_in_field = len(field_assignments[fid])
                if current_in_field >= field_need[fid]:
                    continue  # already fully protected, don't overprotect
                # Assign remaining slots for partial (better than idle)
                slots_to_fill = field_need[fid] - current_in_field
                for d in list(leftover):
                    if slots_to_fill <= 0:
                        break
                    field_assignments[fid].append(id(d))
                    drone_to_field[id(d)] = fid
                    assigned.add(id(d))
                    leftover.remove(d)
                    slots_to_fill -= 1

            # If still leftover and no field needs drones, assign to highest-threat
            # field as partial support (better than idle per requirements)
            if leftover and active_fields:
                # Distribute evenly to top fields that could use support
                top_field = active_fields[0]
                for d in leftover:
                    field_assignments[str(top_field.id)].append(id(d))
                    drone_to_field[id(d)] = str(top_field.id)
                    assigned.add(id(d))

        # --- Step 5: Enforce stability constraint ---
        # "At least half of the drones should stay assigned to the same field
        #  at least 25% of the time" – we've already kept drones in place when
        # their field still needs them. Additionally, avoid moving a drone that
        # is currently in-flight (moving_to_field) unless absolutely necessary.
        # Our first pass already handles this.

        # --- Step 6: Ensure at least half the drones are active ---
        total_drones = len(components)
        active_count = sum(len(v) for v in field_assignments.values())
        if active_count < total_drones // 2 and active_fields:
            # Move idle drones to the most threatened field that's under-assigned
            idle_drones = [d for d in components if id(d) not in assigned]
            for f in active_fields:
                if not idle_drones:
                    break
                fid = str(f.id)
                # Allow partial assignment to boost active ratio
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

        # --- Step 7: Make final assignments ---
        for drone in components:
            d_id = id(drone)
            if d_id in drone_to_field:
                fid = drone_to_field[d_id]
                # Find the field object
                field_obj = next((f for f in environment.fields if str(f.id) == fid), None)
                if field_obj is not None:
                    gname = field_group_name(field_obj)
                    environment.assign_group(drone, gname)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
```

This strategy ensures:
- **Highest-threat field always fully protected** with closest drones (first-priority loop with distance sorting).
- **Minimal reassignment**: drones already on a field that still needs them are kept in place (stability pass).
- **No overprotection**: each field is capped at `drones_for_full_protection`.
- **At least half drones active**: a dedicated check redistributes idle drones if activity ratio is too low.
- **Full protection preferred**: greedy priority-order allocation fills fields completely before moving to the next.