Reasoning and strategy

Problem observations:
- Drones must be partitioned into idle and one group per threatened field: "protecting {field.id}".
- We must always fully protect the most threatened fields (up to drones_for_full_protection per field) using the closest available drones.
- We should avoid over-allocating drones to a field beyond its drones_for_full_protection.
- At least half of the drones should be used for protection most of the time, but not at the expense of excessive churn (drones moving fields too often). We should favor preserving previous protections when feasible.
- Each drone must be assigned exactly once per step.

Strategy description:
- Determine the set of threatened fields (threat_level > 0) and sort them by threat level descending.
- Prepare a deterministic final assignment mapping for every drone (only one group per drone).
- Start with a “keep” pass: for each threatened field, keep as many drones already protecting that field as possible, up to that field’s drones_for_full_protection. These drones are assigned to the corresponding protecting group.
- Then, for each threatened field in order, if the field is not yet fully protected, assign the closest drones that are not currently protecting that field until the field reaches drones_for_full_protection. Use a memory map to prefer drones that previously protected the same field (to reduce churn).
- After attempting to fully protect all fields, ensure we meet the target_protected_count = ceil(N/2). If not, allocate additional drones (closest to the remaining fields) up to each field’s drones_for_full_protection limit, in threat order.
- All drones not assigned to a protecting group become idle. Update a per-drone memory mapping to bias future allocations.
- Finally, apply environment.assign_group for every drone exactly once using the finalized groups.

This approach guarantees:
- The most threatened field(s) are fully protected when possible.
- Drones are allocated by proximity and with memory to reduce unnecessary moves.
- No drone is assigned to multiple groups in a single step.

Python code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map from drone_id (id(drone)) to field_id they last protected (or None)
        self._last_protected_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather all fields with positive threat level
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        total_drones = len(components)
        target_protected_count = (total_drones + 1) // 2  # ceil(N/2)

        # If no threats, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
                self._last_protected_by_drone[id(c)] = None
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # Helper to compute field center
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        # Current protection counts by field (based on current state)
        current_protecting_by_field = {fld.id: [] for fld in threatened_fields}
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                tid = c.target_id
                for fld in threatened_fields:
                    if fld.id == tid:
                        current_protecting_by_field[tid].append(c)
                        break

        # Helper: distance from drone to field center
        def distance_to_field(drone, f):
            cx, cy = field_center(f)
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return (dx*dx + dy*dy) ** 0.5

        # Final mapping: drone -> target_group (string), start with None
        final_group_for_drone = {id(d): None for d in components}

        # Stage 0: Keep as many current protectors as possible, up to drones_for_full_protection
        for f in threatened_fields:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))
            current_list = current_protecting_by_field.get(field_id, [])
            current_count = len(current_list)

            # Keep current protectors as much as possible (up to max)
            keep_count = min(current_count, max_for_field)
            for d in current_list[:keep_count]:
                final_group_for_drone[id(d)] = f"protecting {field_id}"
                self._last_protected_by_drone[id(d)] = field_id

        # Stage 1: Fill up each threatened field to its max_for_field using closest drones not already protecting that field
        for f in threatened_fields:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))

            # Collect drones currently protecting this field
            current_list = current_protecting_by_field.get(field_id, [])
            currently_assigned = len([d for d in current_list if final_group_for_drone.get(id(d)) == f"protecting {field_id}"])
            # If we already allocated the maximum, skip
            if currently_assigned >= max_for_field:
                # Ensure we have each such drone assigned
                for d in current_list:
                    final_group_for_drone[id(d)] = f"protecting {field_id}"
                    self._last_protected_by_drone[id(d)] = field_id
                continue

            needed = max_for_field - currently_assigned
            if needed <= 0:
                continue

            # Candidates: drones not currently protecting this field
            candidates = [c for c in components if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id)]
            if not candidates:
                continue

            cx, cy = field_center(f)

            def score(drone):
                dx = getattr(drone.location, "x", 0.0) - cx
                dy = getattr(drone.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                last = self._last_protected_by_drone.get(id(drone))
                last_match = 1 if last == field_id else 0
                return (dist, -last_match)

            candidates.sort(key=score)
            chosen = candidates[:needed]

            for d in chosen:
                final_group_for_drone[id(d)] = f"protecting {field_id}"
                self._last_protected_by_drone[id(d)] = field_id

        # Stage 2: Ensure at least target_protected_count drones are protecting something
        currently_protecting = [d for d in components if final_group_for_drone.get(id(d)) and final_group_for_drone.get(id(d)).startswith("protecting")]
        total_protected = len(currently_protecting)

        if total_protected < target_protected_count:
            # Fill other fields in threat order
            for f in threatened_fields:
                if total_protected >= target_protected_count:
                    break
                field_id = f.id
                max_for_field = int(getattr(f, "drones_for_full_protection", 0))

                # Count how many are currently protecting this field (finalized)
                current_for_field = len([d for d in components if final_group_for_drone.get(id(d)) == f"protecting {field_id}"])
                if current_for_field >= max_for_field:
                    continue
                need = min(max_for_field - current_for_field, target_protected_count - total_protected)
                if need <= 0:
                    continue

                candidates = [c for c in components if not (final_group_for_drone.get(id(c)) == f"protecting {field_id}")]
                if not candidates:
                    continue

                cx, cy = field_center(f)

                def score2(drone):
                    dx = getattr(drone.location, "x", 0.0) - cx
                    dy = getattr(drone.location, "y", 0.0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                    last = self._last_protected_by_drone.get(id(drone))
                    last_match = 1 if last == field_id else 0
                    return (dist, -last_match)

                candidates.sort(key=score2)
                chosen = candidates[:need]

                for d in chosen:
                    final_group_for_drone[id(d)] = f"protecting {field_id}"
                    self._last_protected_by_drone[id(d)] = field_id
                    total_protected += 1

        # Stage 3: Any drones not assigned to protecting a field become idle
        for c in components:
            if final_group_for_drone.get(id(c)) is None:
                final_group_for_drone[id(c)] = "idle"
                self._last_protected_by_drone[id(c)] = None
            # If for some reason a drone was assigned to an object but not the correct string, ensure it's set
            # (We already ensured a single assignment per drone.)

        # Apply final assignments (exactly one per drone)
        for c in components:
            target_group = final_group_for_drone.get(id(c), "idle")
            environment.assign_group(c, target_group)
```