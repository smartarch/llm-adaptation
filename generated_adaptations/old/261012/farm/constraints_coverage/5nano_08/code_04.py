from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _distance_to_point(self, drone, x, y):
        # Compute squared distance to avoid sqrt
        loc = getattr(drone, 'location', None)
        if loc is None:
            return float('inf')
        dx = getattr(loc, 'x', None)
        dy = getattr(loc, 'y', None)
        if dx is None or dy is None:
            # Fallback: assume location is a tuple/list [x, y]
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                dx, dy = loc[0], loc[1]
            else:
                return float('inf')
        dx -= x
        dy -= y
        return dx*dx + dy*dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify threatened fields
        fields = getattr(environment, 'fields', [])
        threatened = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        if not threatened:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened.sort(key=lambda f: getattr(f, 'threat_level', 0), reverse=True)

        # Compute field centers
        centers = {}
        for f in threatened:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        total_drones = len(components)
        # Allocate up to full protection for each field in threat order
        counts = {}
        remaining = total_drones
        for f in threatened:
            cap = int(getattr(f, 'drones_for_full_protection', 0))
            if cap <= 0:
                continue
            take = min(cap, remaining)
            counts[f.id] = take
            remaining -= take
            if remaining <= 0:
                break

        assignments = {}

        # Allocate drones to each field based on proximity
        for fid, cnt in counts.items():
            center = centers.get(fid)
            if center is None:
                continue
            unassigned = [d for d in components if d not in assignments]
            unassigned.sort(key=lambda d: self._distance_to_point(d, center[0], center[1]))
            for i in range(min(cnt, len(unassigned))):
                c = unassigned[i]
                assignments[c] = f"protecting {fid}"

        # If drones remain, assign them to the top threatened field to boost protection
        assigned_count = len(assignments)
        remaining_drones = total_drones - assigned_count
        if remaining_drones > 0 and threatened:
            top_id = threatened[0].id
            top_center = centers[top_id]
            unassigned = [d for d in components if d not in assignments]
            unassigned.sort(key=lambda d: self._distance_to_point(d, top_center[0], top_center[1]))
            for i in range(min(remaining_drones, len(unassigned))):
                c = unassigned[i]
                assignments[c] = f"protecting {top_id}"

        # Any drones not assigned to a field become idle
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply assignments
        for c, group in assignments.items():
            environment.assign_group(c, group)