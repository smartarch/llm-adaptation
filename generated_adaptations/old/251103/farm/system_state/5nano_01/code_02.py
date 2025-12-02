import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(fields_with_threat, key=lambda fld: fld.threat_level)

        # Compute how many drones are needed to reach full protection for the top field
        current_protecting = getattr(top_field, "protecting_drones", 0)
        current_arriving = getattr(top_field, "arriving_drones", 0)
        drones_needed = top_field.drones_for_full_protection - (current_protecting + current_arriving)
        if drones_needed < 0:
            drones_needed = 0

        # Center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Determine which drones are already allocated to the top field
        allocated_to_top = set()
        for d in components:
            if d.state in ("protecting", "moving_to_field") and d.target_id == top_field.id:
                allocated_to_top.add(d)

        # Build candidate pool: drones not currently allocated to the top field
        candidates = []
        for d in components:
            if d in allocated_to_top:
                continue
            loc = getattr(d, "location", None)
            if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                dist = math.hypot(loc.x - cx, loc.y - cy)
            else:
                dist = float("inf")
            candidates.append((dist, d))
        candidates.sort(key=lambda t: t[0])

        # Compute how many more drones we should assign to top field
        current_top_count = len(allocated_to_top)
        needed_to_fill = max(0, top_field.drones_for_full_protection - current_top_count)

        to_protect = set(allocated_to_top)
        # Add the closest drones up to the needed amount
        for dist, d in candidates:
            if len(to_protect) >= top_field.drones_for_full_protection:
                break
            to_protect.add(d)

        # Assign groups
        for drone in components:
            if drone in to_protect:
                environment.assign_group(drone, f"protecting {top_field.id}")
            else:
                environment.assign_group(drone, "idle")