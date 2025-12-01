import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0) for which a protection group exists
        threatened = []
        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > 0:
                group_name = f"protecting {field.id}"
                if group_name in group_ids:
                    threatened.append(field)

        if not threatened:
            # No valid threatened fields to protect; idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level (desc), break ties by id for determinism
        threatened.sort(key=lambda f: (getattr(f, "threat_level", 0.0), getattr(f, "id", "")), reverse=True)

        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # assigned_by_field: field.id -> set of drones assigned to protect that field
        assigned_by_field = {field.id: set() for field in threatened}
        allocated = set()

        # Step 1: Preserve drones already protecting a field (they should remain protecting)
        for field in threatened:
            fid = field.id
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    assigned_by_field[fid].add(d)
                    allocated.add(d)

        # Step 2: For each field in priority order, fill up to drones_for_full_protection
        for field in threatened:
            fid = field.id
            current = len(assigned_by_field[fid])
            required = int(getattr(field, "drones_for_full_protection", 0))
            needed = max(0, required - current)
            if needed <= 0:
                continue

            # Build candidate pool: drones not yet allocated to any field
            candidates = [d for d in components if d not in allocated]
            # If top field already has some drones, we still consider all unallocated drones
            # Sort candidates by distance to this field
            candidates.sort(key=lambda d: distance_to_field(d, field))

            for d in candidates[:needed]:
                assigned_by_field[fid].add(d)
                allocated.add(d)

        # Step 3: Assign groups based on final allocations
        # If a drone is assigned to a field, give it the corresponding protection group.
        # Otherwise, idle it.
        for d in components:
            assigned = None
            for field in threatened:
                if d in assigned_by_field[field.id]:
                    group_name = f"protecting {field.id}"
                    # Safety: ensure the group name is valid
                    if group_name in group_ids:
                        assigned = group_name
                    else:
                        assigned = None
                    break
            if assigned is not None:
                environment.assign_group(d, assigned)
            else:
                environment.assign_group(d, "idle")