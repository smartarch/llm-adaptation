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

        def dist_to_center(drone, center):
            dx = getattr(drone.location, "x", 0.0) - center[0]
            dy = getattr(drone.location, "y", 0.0) - center[1]
            return math.hypot(dx, dy)

        # Map field_id -> list of drones allocated to protect that field
        assign_map = {fld.id: [] for fld in fields_sorted}
        allocated = set()

        # Iterate fields in threat order and allocate drones to fully protect each
        for fld in fields_sorted:
            need = int(getattr(fld, "drones_for_full_protection", 0))
            if need <= 0:
                continue

            center = field_center(fld)

            # Drones currently targeting this field
            current = [d for d in components if getattr(d, "target_id", None) == fld.id]
            chosen = list(current)

            # Trim if we have more than needed
            if len(chosen) > need:
                chosen = chosen[:need]

            # If we still need more drones, pick from the closest available ones
            if len(chosen) < need:
                remaining = [d for d in components if d not in allocated and d not in chosen]
                remaining.sort(key=lambda d: dist_to_center(d, center))
                needed_more = need - len(chosen)
                chosen.extend(remaining[:needed_more])

            # Mark allocation
            for d in chosen:
                allocated.add(d)
                assign_map[fld.id].append(d)

        # Apply groups: assign each allocated drone to the corresponding protecting group
        for fld in fields_sorted:
            group_name = f"protecting {fld.id}"
            for d in assign_map.get(fld.id, []):
                environment.assign_group(d, group_name)

        # All other drones idle
        for d in components:
            if d not in allocated:
                environment.assign_group(d, "idle")