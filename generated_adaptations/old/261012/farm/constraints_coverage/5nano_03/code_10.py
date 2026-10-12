import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"

        # Build list of threatened fields that have a valid protection group
        threatened = []
        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > 0:
                gid = f"protecting {field.id}"
                if gid in group_ids:
                    threatened.append(field)

        if not threatened:
            # No valid threatened fields; idle all drones if possible
            if idle_group in group_ids:
                for d in components:
                    environment.assign_group(d, idle_group)
            else:
                # Fallback: assign to the first available group to avoid errors
                if group_ids:
                    fallback_group = group_ids[0]
                    for d in components:
                        environment.assign_group(d, fallback_group)
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Helpers to compute field centers and distances
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(d, f):
            cx, cy = field_center(f)
            dx = getattr(d.location, "x", 0.0) - cx
            dy = getattr(d.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Per-field allocations
        allocated_by_field = {f.id: set() for f in threatened}
        allocated_all = set()

        # Step 0: (Optional) preserve drones already protecting a field (but allow reallocation)
        # We won't lock any drone to a field here; we'll recalculate allocations below.

        # Step 1: Allocate to the top field to fully protect it
        top_field = threatened[0]
        top_id = top_field.id
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Current protection on top field (drones currently protecting it)
        current_top = set()
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_id:
                current_top.add(d)
        allocated_by_field[top_id] = set(current_top)
        allocated_all.update(current_top)

        need_top = max(0, required_top - len(allocated_by_field[top_id]))
        if need_top > 0:
            # Candidates: all drones not already allocated to top field
            candidates = [d for d in components if d not in allocated_by_field[top_id]]
            candidates.sort(key=lambda d: dist_to_field(d, top_field))

            for d in candidates[:need_top]:
                allocated_by_field[top_id].add(d)
                allocated_all.add(d)

        # Step 2: Allocate remaining drones to other threatened fields in threat order
        for f in threatened[1:]:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            current = len(allocated_by_field.get(fid, set()))
            need = max(0, required - current)
            if need <= 0:
                continue

            # Candidates: drones not yet allocated to any field
            candidates = [d for d in components if d not in allocated_all]
            candidates.sort(key=lambda d: dist_to_field(d, f))

            if fid not in allocated_by_field:
                allocated_by_field[fid] = set()

            for d in candidates[:need]:
                allocated_by_field[fid].add(d)
                allocated_all.add(d)

        # Step 3: Assign groups based on final allocations
        # For each drone, assign to its corresponding protection group if allocated;
        # otherwise assign to idle (or fallback to a valid group if needed).
        for d in components:
            assigned_group = None
            for f in threatened:
                if d in allocated_by_field.get(f.id, set()):
                    g = f"protecting {f.id}"
                    if g in group_ids:
                        assigned_group = g
                    break

            if assigned_group is not None:
                environment.assign_group(d, assigned_group)
            else:
                # No allocation; try idle
                if idle_group in group_ids:
                    environment.assign_group(d, idle_group)
                else:
                    # Fallback to the first available group to avoid errors
                    if group_ids:
                        environment.assign_group(d, group_ids[0])