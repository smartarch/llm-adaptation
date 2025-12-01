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

            # Global greedy: fill deficits with closest eligible drones
            while any(deficits.get(fid, 0) > 0 for fid in deficits):
                best = None
                best_dist = float('inf')
                best_info = None  # (field_id, from_field)

                for d in components:
                    if d in plan:
                        continue

                    loc = getattr(d, 'location', None)

                    for f in fields:
                        fid = f.id
                        if deficits.get(fid, 0) <= 0:
                            continue

                        cx, cy = centers[fid]
                        dist = float('inf')
                        if loc is not None:
                            dx = getattr(loc, 'x', 0.0) - cx
                            dy = getattr(loc, 'y', 0.0) - cy
                            dist = math.hypot(dx, dy)

                        # Eligibility
                        if getattr(d, 'state', None) == 'protecting':
                            from_field = getattr(d, 'target_id', None)
                            # Don't move a drone away from the field it's currently protecting
                            if from_field == fid:
                                continue
                            # Can donate only if that field has spare protection
                            if current_protect.get(from_field, 0) <= required_map.get(from_field, 0):
                                continue
                            eligible = True
                        else:
                            from_field = None
                            eligible = True

                        if eligible and dist < best_dist:
                            best = d
                            best_dist = dist
                            best_info = (fid, from_field)

                if best is None:
                    break  # no more eligible moves

                drone = best
                fid, from_field = best_info

                plan[drone] = f"protecting {fid}"
                current_protect[fid] = current_protect.get(fid, 0) + 1
                if from_field is not None:
                    current_protect[from_field] = max(0, current_protect.get(from_field, 0) - 1)

                deficits[fid] = max(0, required_map.get(fid, 0) - current_protect.get(fid, 0))
                if from_field is not None:
                    deficits[from_field] = max(0, required_map.get(from_field, 0) - current_protect.get(from_field, 0))

            # All remaining drones become idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments (exactly one per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)