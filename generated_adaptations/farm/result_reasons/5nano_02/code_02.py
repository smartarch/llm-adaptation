import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones to groups:
        - "idle" for drones idle or not needed
        - "protecting {field_id}" for drones protecting a specific field
        The strategy focuses on fully protecting the top-threat field first, using the closest drones,
        and then allocating to other fields if possible, without overprotection.
        """
        # Gather threatening fields (threat_level > 0)
        fields = getattr(environment, 'fields', [])
        threatening_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        if not threatening_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatening_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper to compute field center
        def center_of_field(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        # Helper to distance from drone to field center
        def dist_to_field(drone, f):
            cx, cy = center_of_field(f)
            x = getattr(drone.location, 'x', None)
            y = getattr(drone.location, 'y', None)
            if x is None or y is None:
                return float('inf')
            return math.hypot(x - cx, y - cy)

        N = len(components)
        # Determine how many drones to allocate to each field (greedy by threat)
        remaining = N
        needs = {}
        for f in threatening_fields:
            need = int(getattr(f, 'drones_for_full_protection', 0))
            if remaining >= need:
                needs[f.id] = need
                remaining -= need
            else:
                needs[f.id] = remaining
                remaining = 0
                # No more drones left to allocate to further fields
        # Ensure all threatening fields exist in needs (even if 0)
        for f in threatening_fields:
            if f.id not in needs:
                needs[f.id] = 0

        # Build final assignment: field_id -> set of drones to protect
        field_to_drones = {f.id: set() for f in threatening_fields}
        already_assigned = set()
        drones = list(components)

        # Assign drones to fields in order of threat (top first)
        for f in threatening_fields:
            limit = int(needs.get(f.id, 0))
            if limit <= 0:
                continue

            # Candidates not yet assigned
            candidates = [d for d in drones if d not in already_assigned]

            # Current drones already targeting this field (among candidates)
            current = [d for d in candidates
                       if (getattr(d, 'state', None) in ('protecting', 'moving_to_field')
                           and getattr(d, 'target_id', None) == f.id)]
            # Sort by distance to this field (closer first)
            current.sort(key=lambda d: dist_to_field(d, f))

            # Keep closest up to limit
            keep = current[:min(limit, len(current))]
            for d in keep:
                field_to_drones[f.id].add(d)
            for d in keep:
                already_assigned.add(d)

            # If more drones are needed for this field, fill from remaining candidates
            remaining_need = limit - len(field_to_drones[f.id])
            if remaining_need > 0:
                non_assigned = [d for d in candidates if d not in field_to_drones[f.id]]
                non_assigned.sort(key=lambda d: dist_to_field(d, f))
                add = non_assigned[:remaining_need]
                for d in add:
                    field_to_drones[f.id].add(d)
                    already_assigned.add(d)

        # Assign groups: those in field_to_drones get "protecting {field_id}"
        # All others get "idle"
        for d in drones:
            assigned_field_id = None
            for fid, ds in field_to_drones.items():
                if d in ds:
                    assigned_field_id = fid
                    break
            if assigned_field_id is not None:
                environment.assign_group(d, f"protecting {assigned_field_id}")
            else:
                environment.assign_group(d, "idle")