from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat (high to low). Tie-breaker by drones_for_full_protection if available
        threat_fields.sort(
            key=lambda f: (
                -getattr(f, "threat_level", 0),
                -getattr(f, "drones_for_full_protection", 0)
            )
        )

        # Helpers: center of a field and distance from a drone to a field center
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_field(drone, field):
            cx, cy = center(field)
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        D = len(components)

        # Determine which fields to fully protect given the total number of drones
        target_fields = []
        used = 0
        for f in threat_fields:
            need = max(0, getattr(f, "drones_for_full_protection", 0))
            if need == 0:
                continue
            if used + need <= D:
                target_fields.append(f)
                used += need
            else:
                break

        # Allocation: field_id -> list of drones
        alloc = {f.id: [] for f in target_fields}
        allocated = set()

        # Step 1: Keep as many currently protecting drones as possible (stickiness)
        for f in target_fields:
            need = getattr(f, "drones_for_full_protection", 0)
            if need <= 0:
                continue
            currently = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
            ]
            currently.sort(key=lambda d: dist_to_field(d, f))
            keep = min(len(currently), need)
            for d in currently[:keep]:
                alloc[f.id].append(d)
                allocated.add(d)

        # Step 2: Fill remaining slots with closest available drones
        for f in target_fields:
            need = max(0, getattr(f, "drones_for_full_protection", 0) - len(alloc[f.id]))
            if need <= 0:
                continue
            candidates = [d for d in components if d not in allocated]
            candidates.sort(key=lambda d: dist_to_field(d, f))
            for d in candidates[:need]:
                alloc[f.id].append(d)
                allocated.add(d)

        # Step 3: Assign groups for protected fields
        for f in target_fields:
            group = f"protecting {f.id}"
            for d in alloc[f.id]:
                environment.assign_group(d, group)

        # Step 4: Remaining drones idle
        for d in components:
            if d not in allocated:
                environment.assign_group(d, "idle")