import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {}
        for f in threatened:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Determine how many drones are currently needed for each field
        needs = {}
        for f in threatened:
            current = sum(1 for d in components if d.target_id == f.id and d.state in ("protecting", "moving_to_field"))
            needs[f.id] = max(0, f.drones_for_full_protection - current)

        # Step 1: continuity - reassign drones already targeting fields that still need protection
        assigned = set()
        for f in threatened:
            if needs[f.id] <= 0:
                continue
            for d in components:
                if d in assigned:
                    continue
                if d.target_id == f.id and d.state in ("protecting", "moving_to_field"):
                    environment.assign_group(d, f"protecting {f.id}")
                    assigned.add(d)
                    needs[f.id] -= 1
                    if needs[f.id] <= 0:
                        break

        # Step 2: fill remaining needs with closest available drones
        for f in threatened:
            if needs[f.id] <= 0:
                continue
            # available drones not yet assigned
            available = [d for d in components if d not in assigned]
            if not available:
                break
            cx, cy = centers[f.id]
            available.sort(key=lambda d: (d.location.x - cx) ** 2 + (d.location.y - cy) ** 2)
            for d in available[:needs[f.id]]:
                environment.assign_group(d, f"protecting {f.id}")
                assigned.add(d)
            needs[f.id] = 0

        # Step 3: idle any drones not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")