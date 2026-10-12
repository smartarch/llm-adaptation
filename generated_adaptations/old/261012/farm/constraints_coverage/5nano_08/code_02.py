from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _distance2(self, p, qx, qy):
        # Compute squared distance to avoid unnecessary sqrt
        lx = getattr(p, 'location', None)
        if lx is None:
            return float('inf')
        # Try attributes x, y first
        x = getattr(lx, 'x', None)
        y = getattr(lx, 'y', None)
        if x is None or y is None:
            # Fallback: assume location is a tuple/list [x, y]
            if isinstance(lx, (list, tuple)) and len(lx) >= 2:
                x, y = lx[0], lx[1]
            else:
                return float('inf')
        dx = x - qx
        dy = y - qy
        return dx*dx + dy*dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level (> 0)
        fields_with_threat = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]
        if not fields_with_threat:
            # No threat fields; idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        top_field = max(fields_with_threat, key=lambda f: getattr(f, 'threat_level', 0))
        top_field_id = top_field.id

        # Field center for distance calculations
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Drones needed for full protection
        needed = int(getattr(top_field, 'drones_for_full_protection', 0))
        if needed <= 0:
            # If field cannot be fully protected (no drones needed), idle all
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Drones currently protecting the top field
        current_protectors = [
            c for c in components
            if getattr(c, 'state', None) == "protecting" and getattr(c, 'target_id', None) == top_field_id
        ]

        # If already fully protected or over-protected, keep current protectors, idle the rest
        assignments = {}
        for c in current_protectors:
            assignments[c] = f"protecting {top_field_id}"

        # If we need more protection, select closest drones to fill the gap
        need_more = max(0, needed - len(current_protectors))
        if need_more > 0:
            # Candidates are drones not already protecting this field
            candidates = [
                c for c in components if c not in current_protectors
            ]
            # Sort by distance to field center
            candidates.sort(key=lambda d: self._distance2(d, cx, cy))
            for i in range(min(need_more, len(candidates))):
                c = candidates[i]
                assignments[c] = f"protecting {top_field_id}"

        # Remaining drones go idle
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply group assignments
        for c, group in assignments.items():
            environment.assign_group(c, group)