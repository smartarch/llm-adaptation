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

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_point(drone, point):
            dx = getattr(drone.location, "x", 0.0) - point[0]
            dy = getattr(drone.location, "y", 0.0) - point[1]
            return math.hypot(dx, dy)

        # Top-threat field
        top_field = fields_sorted[0]
        top_field_id = top_field.id
        top_center = field_center(top_field)

        # Drones needed for top field
        needed_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Drones currently targeting the top field (reserved)
        reserved_top = [d for d in components if getattr(d, "target_id", None) == top_field_id]

        # Decide which drones go to top_field
        assigned_to_top = []

        # If we already have enough reserved, keep exactly 'needed_top' of them
        if len(reserved_top) >= needed_top:
            assigned_to_top = reserved_top[:needed_top]
        else:
            # Keep all reserved, then bring in idle drones (target_id is None)
            assigned_to_top = list(reserved_top)
            remaining_needed = needed_top - len(assigned_to_top)

            if remaining_needed > 0:
                pool = [d for d in components if d not in assigned_to_top and getattr(d, "target_id", None) is None]
                pool.sort(key=lambda d: dist_to_point(d, top_center))
                assigned_to_top.extend(pool[:remaining_needed])

        # After top is filled, prepare to help other threatened fields using idle drones only
        # Map field_id -> center
        centers = {fld.id: field_center(fld) for fld in fields_sorted}
        # Track allocated drones to fields
        allocated_by_field = {fld.id: [] for fld in fields_sorted}
        # Track all allocated drones
        allocated_set = set()

        # Assign top field
        for d in assigned_to_top:
            allocated_by_field[top_field_id].append(d)
            allocated_set.add(d)

        # Now try to help other threatened fields with remaining idle drones
        # Pool of idle drones: those not yet allocated
        pool_idle = [d for d in components if d not in allocated_set and getattr(d, "target_id", None) is None]
        # Sort and allocate to deficits of other fields in threat order
        for fld in fields_sorted[1:]:
            if not pool_idle:
                break
            need = int(getattr(fld, "drones_for_full_protection", 0))
            current = [d for d in components if getattr(d, "target_id", None) == fld.id]
            deficit = max(0, need - len(current))
            if deficit <= 0:
                continue
            center = centers[fld.id]
            pool_idle.sort(key=lambda d: dist_to_point(d, center))
            to_take = min(deficit, len(pool_idle))
            for i in range(to_take):
                d = pool_idle.pop(0)
                allocated_by_field[fld.id].append(d)
                allocated_set.add(d)

        # Build final group assignments
        # Helper: map drone -> field_id it will protect (for allocated drones)
        drone_to_field = {}
        for fid, lst in allocated_by_field.items():
            for d in lst:
                drone_to_field[d] = fid

        # Assign groups
        for d in components:
            if d in drone_to_field:
                fid = drone_to_field[d]
                environment.assign_group(d, f"protecting {fid}")
            else:
                # Preserve existing protection if drone is already targeting a threatened field
                tid = getattr(d, "target_id", None)
                threatened_ids = {fld.id for fld in threat_fields}
                if tid in threatened_ids:
                    environment.assign_group(d, f"protecting {tid}")
                else:
                    environment.assign_group(d, "idle")