import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        plan = {}  # drone -> target_group (exactly one assignment per drone)

        if not fields:
            # No threat: idle all drones
            for d in components:
                plan[d] = "idle"
        else:
            # Precompute field centers and required counts
            centers = {
                f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)
                for f in fields
            }
            required_map = {f.id: int(getattr(f, 'drones_for_full_protection', 0)) for f in fields}

            # Current protection counts per field
            current_protect = {f.id: 0 for f in fields}
            for d in components:
                if getattr(d, 'state', None) == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid in current_protect:
                        current_protect[tid] += 1

            # Initial deficits
            deficits = {f.id: max(0, required_map.get(f.id, 0) - current_protect.get(f.id, 0)) for f in fields}

            # Greedy global assignment: fill deficits with closest candidates
            while any(deficits.get(fid, 0) > 0 for fid in deficits):
                best = None  # (dist, drone, field_id, from_field)
                best_dist = float('inf')

                # Try to find the best candidate across all fields with deficit
                for f in fields:
                    fid = f.id
                    need = deficits.get(fid, 0)
                    if need <= 0:
                        continue
                    cx, cy = centers[fid]

                    for d in components:
                        if d in plan:
                            continue

                        loc = getattr(d, 'location', None)
                        dist = float('inf')
                        if loc is not None:
                            dx = getattr(loc, 'x', 0.0) - cx
                            dy = getattr(loc, 'y', 0.0) - cy
                            dist = math.hypot(dx, dy)

                        # If drone is already protecting this field, skip (it's already counted)
                        if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == fid:
                            continue

                        from_field = None
                        if getattr(d, 'state', None) == 'protecting':
                            from_field = getattr(d, 'target_id', None)
                            # We can only sacrifice from a field if it has spare protection
                            if current_protect.get(from_field, 0) <= required_map.get(from_field, 0):
                                continue

                        # Candidate found
                        if dist < best_dist:
                            best = (d, fid, from_field, dist)
                            best_dist = dist

                if best is None:
                    # No more reallocations possible under current constraints
                    break

                drone, field_id, from_field, dist = best
                plan[drone] = f"protecting {field_id}"

                # Update counts for the plan
                if from_field is not None:
                    current_protect[from_field] = max(0, current_protect.get(from_field, 0) - 1)

                current_protect[field_id] = current_protect.get(field_id, 0) + 1

                # Update deficits for the affected fields
                deficits[field_id] = max(0, required_map.get(field_id, 0) - current_protect.get(field_id, 0))
                if from_field is not None:
                    deficits[from_field] = max(0, required_map.get(from_field, 0) - current_protect.get(from_field, 0))

            # All remaining drones become idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments (exactly one assignment per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)