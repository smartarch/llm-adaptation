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
            # Precompute field centers
            centers = {
                f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)
                for f in fields_with_threat
            }

            # Current protection counts per field
            current_protect = {f.id: 0 for f in fields_with_threat}
            for d in components:
                if getattr(d, 'state', None) == 'protecting':
                    tid = getattr(d, 'target_id', None)
                    if tid in current_protect:
                        current_protect[tid] += 1

            # Sort fields by threat level (highest first)
            fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

            assigned = set()  # drones already assigned in this plan

            for f in fields_sorted:
                required = int(getattr(f, 'drones_for_full_protection', 0))
                if required <= 0:
                    continue
                current = current_protect.get(f.id, 0)
                needed = max(0, required - int(current))
                if needed <= 0:
                    continue

                cx, cy = centers[f.id]

                # Build candidate drones: not currently protecting any field, and not already planned
                candidates = []
                for d in components:
                    if d in plan:
                        continue
                    if getattr(d, 'state', None) == 'protecting':
                        # Skip drones already protecting a field
                        continue
                    loc = getattr(d, 'location', None)
                    if loc is None:
                        dist = float('inf')
                    else:
                        dx = getattr(loc, 'x', 0.0) - cx
                        dy = getattr(loc, 'y', 0.0) - cy
                        dist = math.hypot(dx, dy)
                    candidates.append((dist, d))

                candidates.sort(key=lambda t: t[0])

                to_take = min(needed, len(candidates))
                for i in range(to_take):
                    drone = candidates[i][1]
                    plan[drone] = f"protecting {f.id}"
                    assigned.add(drone)

            # For all drones not in plan, set to idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply exactly one assignment per drone
        for d, grp in plan.items():
            environment.assign_group(d, grp)