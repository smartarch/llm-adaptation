from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Helper: distance from drone to a point
        def dist_to(point, drone):
            dx = (getattr(drone.location, 'x', 0.0) - point[0])
            dy = (getattr(drone.location, 'y', 0.0) - point[1])
            return math.hypot(dx, dy)

        # Helper: current protecting count for a given field
        def current_protecting_count(field_id):
            count = 0
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                    count += 1
            return count

        # Build list of fields with threat > 0, sorted by threat descending
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        allocated_top = set()  # drones allocated to top field
        allocated_by_field = {}  # field_id -> set of drones allocated to protect it

        # If there is at least one threatening field, allocate for the top field first
        top_field = threat_fields[0] if threat_fields else None

        if top_field is not None:
            top_id = top_field.id
            required = int(getattr(top_field, "drones_for_full_protection", 0))
            current = current_protecting_count(top_id)

            # Drones currently protecting top_field
            currently_top = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id]
            for d in currently_top:
                allocated_top.add(d)

            # If we need more drones, pick closest from the rest
            if current < required:
                needed = min(required - current, len(components) - len(allocated_top))
                center = field_center(top_field)
                # Candidates are those not already allocated to top_field
                candidates = [d for d in components if d not in allocated_top]
                candidates.sort(key=lambda d: dist_to(center, d))
                for d in candidates[:needed]:
                    allocated_top.add(d)

        # Initialize allocation mapping for other fields (excluding the top field)
        for f in threat_fields:
            if top_field is not None and f.id == top_field.id:
                continue
            allocated_by_field[f.id] = set()

        # Add any drones already protecting other fields to their respective allocations
        for d in components:
            if d.state == "protecting":
                fid = getattr(d, "target_id", None)
                if fid is None:
                    continue
                if top_field is not None and fid == top_field.id:
                    # already accounted in allocated_top
                    continue
                if fid in allocated_by_field:
                    allocated_by_field[fid].add(d)

        # For remaining fields, try to allocate additional drones up to full protection
        for f in threat_fields:
            if top_field is not None and f.id == top_field.id:
                continue
            field_id = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            current = len(allocated_by_field.get(field_id, set()))
            # Also consider drones currently protecting this field
            current += current_protecting_count(field_id)
            if field_id not in allocated_by_field:
                allocated_by_field[field_id] = set()
            if current < required:
                needed = min(required - current, len(components) - len(allocated_top) - sum(len(s) for s in allocated_by_field.values()))
                center = field_center(f)
                # Pool of candidates not yet allocated to any field
                allocated_so_far = set(allocated_top)
                for s in allocated_by_field.values():
                    allocated_so_far.update(s)
                candidates = [d for d in components if d not in allocated_so_far]
                candidates.sort(key=lambda d: dist_to(center, d))
                for d in candidates[:needed]:
                    allocated_by_field[field_id].add(d)

        # Final grouping assignments
        # Assign top field protection
        if top_field is not None:
            for d in allocated_top:
                environment.assign_group(d, f"protecting {top_field.id}")

        # Assign other fields
        for f in threat_fields:
            if top_field is not None and f.id == top_field.id:
                continue
            for d in allocated_by_field.get(f.id, set()):
                environment.assign_group(d, f"protecting {f.id}")

        # Any drone not allocated to any protection becomes idle
        allocated_all = set(allocated_top)
        for s in allocated_by_field.values():
            allocated_all.update(s)

        for d in components:
            if d not in allocated_all:
                environment.assign_group(d, "idle")