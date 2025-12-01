import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields_with_threat = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Map field_id -> field and compute centers
        centers = {}
        for f in fields_with_threat:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Count current drones protecting each field
        current_protect = {f.id: 0 for f in fields_with_threat}
        for d in components:
            if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) is not None:
                tid = d.target_id
                if tid in current_protect:
                    current_protect[tid] += 1

        # Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

        # Track which drones we move to protect the top fields
        assigned_to_top = set()
        used_drones = set()

        for f in fields_sorted:
            required = int(getattr(f, 'drones_for_full_protection', 0))
            if required <= 0:
                continue
            current = current_protect.get(f.id, 0)
            needed = max(0, required - int(current))
            if needed <= 0:
                # Already fully protected; keep existing drones here
                continue

            cx, cy = centers[f.id]
            # Build candidate drones (exclude those already protecting this field)
            candidates = []
            for idx, d in enumerate(components):
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == f.id:
                    # already protecting this field
                    continue
                loc = getattr(d, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0.0) - cx
                    dy = getattr(loc, 'y', 0.0) - cy
                    dist = math.hypot(dx, dy)
                candidates.append((dist, idx, d))

            candidates.sort(key=lambda t: t[0])

            # Assign closest drones to this field
            num_to_assign = min(needed, len(candidates))
            for i in range(num_to_assign):
                _, _, drone = candidates[i]
                environment.assign_group(drone, f"protecting {f.id}")
                assigned_to_top.add(drone)
                used_drones.add(drone)

        # After prioritizing top field(s), assign remaining drones to idle
        for d in components:
            if d in used_drones or d in assigned_to_top:
                continue
            environment.assign_group(d, "idle")