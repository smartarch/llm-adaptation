import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"

        # Collect threatened fields that have a valid protection group
        threatened = []
        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > 0:
                if f"protecting {field.id}" in group_ids:
                    threatened.append(field)

        # If no valid threatened fields, idle all drones (where possible)
        if not threatened:
            if idle_group in group_ids:
                for d in components:
                    environment.assign_group(d, idle_group)
            return

        # Sort fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Helpers to compute distance to field center
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(d, f):
            cx, cy = field_center(f)
            dx = getattr(d.location, "x", 0.0) - cx
            dy = getattr(d.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # allocated: field_id -> set of drones assigned to protect that field
        allocated = {f.id: set() for f in threatened}

        # Step 1: Keep drones already protecting a field allocated to that field
        for f in threatened:
            fid = f.id
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    allocated[fid].add(d)

        # Step 2: For each field in priority order, allocate additional drones
        all_drones = list(components)
        for f in threatened:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            current = len(allocated[fid])
            need = max(0, required - current)
            if need <= 0:
                continue

            # Candidates: drones not already allocated to this field
            candidates = [d for d in all_drones if d not in allocated[fid]]
            # Sort by distance to this field
            candidates.sort(key=lambda d: dist_to_field(d, f))

            # Allocate up to 'need' drones
            for d in candidates[:need]:
                allocated[fid].add(d)

        # Step 3: Assign groups based on final allocations
        for d in components:
            assigned_group = None
            for f in threatened:
                if d in allocated[f.id]:
                    group_name = f"protecting {f.id}"
                    if group_name in group_ids:
                        assigned_group = group_name
                    break
            if assigned_group is not None:
                environment.assign_group(d, assigned_group)
            else:
                if idle_group in group_ids:
                    environment.assign_group(d, idle_group)