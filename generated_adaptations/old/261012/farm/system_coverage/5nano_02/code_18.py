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
                best_pair = None
                best_score = float('-inf')

                # Evaluate all possible moves to any field with deficit
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
                            # Can't move away from the same field
                            if from_field == fid:
                                continue
                            # Allow only if that field has spare protection
                            if current_protect.get(from_field, 0) <= required_map.get(from_field, 0):
                                continue
                        else:
                            from_field = None

                        # Compute a score: higher deficit and higher threat level preferred, closer distance preferred
                        threat_level = max(0.0, getattr(f, 'threat_level', 0.0))
                        threat_score = threat_level * 100.0  # scale threat to a useful value
                        deficit = deficits.get(fid, 0)
                        score = threat_score * deficit - dist  # distance weight is 1.0

                        if score > best_score:
                            best_score = score
                            best_pair = (d, fid, from_field, dist)

                if best_pair is None:
                    break  # no more eligible moves

                drone, fid, from_field, dist = best_pair

                plan[drone] = f"protecting {fid}"
                deficits[fid] = max(0, deficits.get(fid, 0) - 1)
                current_protect[fid] = current_protect.get(fid, 0) + 1
                if from_field is not None:
                    current_protect[from_field] = max(0, current_protect.get(from_field, 0) - 1)

                # Update deficits for from_field if it exists
                if from_field is not None:
                    deficits[from_field] = max(0, required_map.get(from_field, 0) - current_protect.get(from_field, 0))

            # All remaining drones become idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments (exactly one per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)