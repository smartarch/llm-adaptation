import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"

        # Collect threatened fields that have a valid protection group
        threatened = []
        field_by_id = {}
        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > 0:
                gid = f"protecting {field.id}"
                if gid in group_ids:
                    threatened.append(field)
                    field_by_id[field.id] = field

        # If no valid threatened fields, idle all drones (if possible)
        if not threatened:
            if idle_group in group_ids:
                for d in components:
                    environment.assign_group(d, idle_group)
            else:
                # Fallback: assign to the first available protecting group if no idle
                if group_ids:
                    fallback_group = group_ids[0]
                    for d in components:
                        environment.assign_group(d, fallback_group)
            return

        # Sort fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Helpers
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(d, f):
            cx, cy = field_center(f)
            dx = getattr(d.location, "x", 0.0) - cx
            dy = getattr(d.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # allocated_by_field: field.id -> set of drones assigned to protect that field
        allocated_by_field = {f.id: set() for f in threatened}
        allocated_all = set()

        # Step 1: Preserve drones already protecting a field
        for f in threatened:
            fid = f.id
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    allocated_by_field[fid].add(d)
                    allocated_all.add(d)

        # Step 2: For each field in priority order, allocate additional drones
        for f in threatened:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            current = len(allocated_by_field[fid])
            need = max(0, required - current)
            if need <= 0:
                continue

            # Candidates: drones not yet allocated to any field
            candidates = [d for d in components if d not in allocated_all]
            # Sort by distance to this field
            candidates.sort(key=lambda d: dist_to_field(d, f))

            for d in candidates[:need]:
                allocated_by_field[fid].add(d)
                allocated_all.add(d)

        # Step 3: Assign groups based on final allocations
        for d in components:
            assigned_group = None
            # Determine if the drone is allocated to any field (in priority order)
            for f in threatened:
                if d in allocated_by_field[f.id]:
                    g = f"protecting {f.id}"
                    if g in group_ids:
                        assigned_group = g
                    break

            if assigned_group is not None:
                environment.assign_group(d, assigned_group)
            else:
                # Fallback: idle if available, else assign to top field's protecting group
                if idle_group in group_ids:
                    environment.assign_group(d, idle_group)
                else:
                    # Fallback to top-threat field's group if possible
                    top_field = threatened[0]
                    g = f"protecting {top_field.id}"
                    if g in group_ids:
                        environment.assign_group(d, g)
                    else:
                        # No valid group available; pick the first available group as last resort
                        if group_ids:
                            environment.assign_group(d, group_ids[0])
                        else:
                            # As a last resort, do nothing (should not happen in typical tests)
                            pass