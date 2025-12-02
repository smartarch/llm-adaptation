from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist2(drone, tx, ty):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", None)
            y = getattr(loc, "y", None)
            if x is None or y is None:
                if isinstance(loc, dict):
                    x = loc.get("x", 0.0)
                    y = loc.get("y", 0.0)
            if x is None or y is None:
                return float("inf")
            dx = x - tx
            dy = y - ty
            return dx * dx + dy * dy

        # Gather threat fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Map field_id -> field object for quick lookup
        field_by_id = {f.id: f for f in threat_fields}
        # Top field: highest threat level
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # Current protection counts per field
        counts = {f.id: 0 for f in threat_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in counts:
                    counts[tid] = counts.get(tid, 0) + 1

        top_current = counts.get(top_field.id, 0)
        top_need = max(0, getattr(top_field, "drones_for_full_protection", 0) - top_current)

        assigned = set()

        # Slack detection: safe to move one drone away from a field if counts[field] > drones_for_full_protection
        def field_slack(field_id):
            need = getattr(field_by_id[field_id], "drones_for_full_protection", 0)
            return max(0, counts.get(field_id, 0) - need)

        def drone_has_slack(d):
            # If drone is already protecting some field, is that field slack enough to spare one drone?
            if getattr(d, "state", None) == "protecting":
                old = getattr(d, "target_id", None)
                if old in counts and field_slack(old) > 0:
                    return True
            return False

        # Phase 1: Fill top field with closest drones, preferring drones from slack fields
        tx, ty = field_center(top_field)
        # Exclude drones already protecting the top field
        candidates_for_top = [d for d in components if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id)]
        # Sort by (slack preference, distance)
        candidates_for_top.sort(key=lambda d: (0 if drone_has_slack(d) else 1, dist2(d, tx, ty)))
        for d in candidates_for_top:
            if top_need <= 0:
                break
            environment.assign_group(d, f"protecting {top_field.id}")
            assigned.add(d)
            old_target = getattr(d, "target_id", None)
            if old_target is not None and old_target != top_field.id:
                counts[old_target] = max(0, counts.get(old_target, 0) - 1)
            counts[top_field.id] = counts.get(top_field.id, 0) + 1
            top_need -= 1

        # Build list of remaining drones
        available = [d for d in components if d not in assigned]

        # Phase 2: Allocate to other threat fields in threat order
        other_fields = [f for f in threat_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for field in other_fields:
            cur = counts.get(field.id, 0)
            need = max(0, getattr(field, "drones_for_full_protection", 0) - cur)
            if need <= 0:
                continue
            fx, fy = field_center(field)
            # Sort available drones by (safe to move, distance)
            def drone_safe_for_field(d):
                # Drone is safe to move if it's idle or from a field that has slack
                if getattr(d, "state", None) == "protecting":
                    old = getattr(d, "target_id", None)
                    if old in field_by_id and field_slack(old) > 0:
                        return True
                    return False
                return True  # idle is safe to allocate
            available.sort(key=lambda d: (0 if drone_safe_for_field(d) else 1, dist2(d, fx, fy)))
            take = min(need, len(available))
            for _ in range(take):
                d = available.pop(0)
                old_target = getattr(d, "target_id", None)
                if old_target is not None and old_target != field.id:
                    counts[old_target] = max(0, counts.get(old_target, 0) - 1)
                environment.assign_group(d, f"protecting {field.id}")
                assigned.add(d)
                counts[field.id] = counts.get(field.id, 0) + 1
            if not available:
                break

        # Phase 3: Remaining drones idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")