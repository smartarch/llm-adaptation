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

            # Compute how many we can safely remove from each field (to reallocate)
            required_map = {f.id: int(getattr(f, 'drones_for_full_protection', 0)) for f in fields_with_threat}
            allowed_removals = {}
            for f in fields_sorted:
                rem = max(0, current_protect.get(f.id, 0) - required_map.get(f.id, 0))
                if rem > 0:
                    allowed_removals[f.id] = rem

            # Build plan by trying to fill top fields with closest available drones
            for f in fields_sorted:
                needed = max(0, required_map.get(f.id, 0) - current_protect.get(f.id, 0))
                if needed == 0:
                    continue

                cx, cy = centers[f.id]

                # Build candidate list
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
                        gid = getattr(d, 'target_id', None)
                        if gid == f.id:
                            # Already protecting this field; skip
                            continue
                        # Can we sacrifice from its current field?
                        if allowed_removals.get(gid, 0) > 0:
                            candidates.append((dist, d, gid))
                    else:
                        candidates.append((dist, d, None))

                candidates.sort(key=lambda t: t[0])

                take = min(needed, len(candidates))
                for i in range(take):
                    dist, d, from_field = candidates[i]
                    plan[d] = f"protecting {f.id}"
                    if from_field is not None:
                        # We removed one drone from from_field
                        current_protect[from_field] = current_protect.get(from_field, 0) - 1
                        allowed_removals[from_field] = allowed_removals.get(from_field, 0) - 1
                        if allowed_removals[from_field] < 0:
                            allowed_removals[from_field] = 0
                    current_protect[f.id] = current_protect.get(f.id, 0) + 1

            # After planning, assign all drones not in plan to idle
            for d in components:
                if d not in plan:
                    plan[d] = "idle"

        # Apply assignments (exactly one per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)