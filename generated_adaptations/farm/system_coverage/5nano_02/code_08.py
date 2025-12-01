import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields_with_threat = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        plan = {}  # drone -> target_group (exactly one assignment per drone)

        if not fields_with_threat:
            # No threat: idle all drones
            for d in components:
                plan[d] = "idle"
        else:
            # Precompute field centers and targets
            centers = {
                f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)
                for f in fields_with_threat
            }
            required_map = {f.id: int(getattr(f, 'drones_for_full_protection', 0)) for f in fields_with_threat}

            # Current protection counts per field
            current_protect = {f.id: 0 for f in fields_with_threat}
            for d in components:
                if getattr(d, 'state', None) == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid in current_protect:
                        current_protect[tid] += 1

            # Sort fields by threat level (highest first)
            fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

            # Build plan sequentially for each field
            for f in fields_sorted:
                needed = max(0, required_map.get(f.id, 0) - current_protect.get(f.id, 0))
                if needed == 0:
                    continue

                cx, cy = centers[f.id]

                candidates = []
                for d in components:
                    if d in plan:
                        continue
                    loc = getattr(d, 'location', None)
                    dist = float('inf')
                    if loc is not None:
                        dx = getattr(loc, 'x', 0.0) - cx
                        dy = getattr(loc, 'y', 0.0) - cy
                        dist = math.hypot(dx, dy)

                    if getattr(d, 'state', None) == 'protecting':
                        from_field = getattr(d, 'target_id', None)
                        if from_field == f.id:
                            # Already protecting this field
                            continue
                        # Can we sacrifice from from_field? Only if it has spare protection
                        if current_protect.get(from_field, 0) > required_map.get(from_field, 0):
                            candidates.append((dist, d, from_field))
                    else:
                        # Idle drone
                        candidates.append((dist, d, None))

                candidates.sort(key=lambda t: t[0])

                take = min(needed, len(candidates))
                for i in range(take):
                    dist, drone, from_field = candidates[i]
                    plan[drone] = f"protecting {f.id}"
                    current_protect[f.id] = current_protect.get(f.id, 0) + 1
                    if from_field is not None:
                        current_protect[from_field] = max(0, current_protect.get(from_field, 0) - 1)

            # All remaining drones become idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments with exactly one group per drone
        for d, grp in plan.items():
            environment.assign_group(d, grp)