import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(
            threat_fields,
            key=lambda f: getattr(f, "threat_level", 0),
            reverse=True
        )

        # Helpers to compute field centers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Distance from a drone to a field center
        def dist_to_center(drone, center):
            dx = getattr(drone.location, "x", 0.0) - center[0]
            dy = getattr(drone.location, "y", 0.0) - center[1]
            return math.hypot(dx, dy)

        # Build reserved mapping: drones already targeting a field stay with that field
        reserved_by_field = {fld.id: [] for fld in fields_sorted}
        for d in components:
            tid = getattr(d, "target_id", None)
            if tid in reserved_by_field:
                reserved_by_field[tid].append(d)

        allocated = set()
        assigned_map = {}  # drone -> field_id it will protect

        # Mark reserved drones as allocated to their fields
        for fid, drones in reserved_by_field.items():
            for d in drones:
                allocated.add(d)
                assigned_map[d] = fid

        # Compute deficits for each field: how many more drones are needed
        deficits = {}
        for fld in fields_sorted:
            need = int(getattr(fld, "drones_for_full_protection", 0))
            deficits[fld.id] = max(0, need - len(reserved_by_field.get(fld.id, [])))

        # Pool of drones not yet allocated
        pool = [d for d in components if d not in allocated]

        # Allocate drones to deficits using a round-robin, closest-first approach
        # Continue until no deficits or pool is empty
        centers = {fld.id: field_center(fld) for fld in fields_sorted}
        while True:
            progressed = False
            for fld in fields_sorted:
                fid = fld.id
                if deficits[fid] > 0 and pool:
                    center = centers[fid]
                    # Choose the closest drone in the pool to this field
                    best = min(pool, key=lambda d: dist_to_center(d, center))
                    pool.remove(best)
                    allocated.add(best)
                    assigned_map[best] = fid
                    deficits[fid] -= 1
                    progressed = True
            if not progressed:
                break

        # Apply groups: assigned drones go to their protecting group; others idle
        for d, fid in assigned_map.items():
            environment.assign_group(d, f"protecting {fid}")

        for d in components:
            if d not in allocated:
                environment.assign_group(d, "idle")