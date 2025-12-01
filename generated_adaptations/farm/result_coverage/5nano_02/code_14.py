import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in threatened}

        # Determine how many drones are currently needed for each field
        needs = {}
        for f in threatened:
            current = sum(
                1
                for d in components
                if d.target_id == f.id and d.state in ("protecting", "moving_to_field")
            )
            needs[f.id] = max(0, f.drones_for_full_protection - current)

        assigned = set()

        # Greedy loop: repeatedly allocate the closest available drone to the highest-need field
        while True:
            # Fields that still need protection
            need_fields = [f for f in threatened if needs.get(f.id, 0) > 0]
            if not need_fields:
                break

            # Choose the field with the highest threat (tie-break by smaller required count)
            need_fields.sort(key=lambda f: (f.threat_level, -f.drones_for_full_protection), reverse=True)
            f = need_fields[0]

            # Find the closest available drone to this field
            fx, fy = centers[f.id]
            best = None
            best_dist = None
            for d in components:
                if d in assigned:
                    continue
                dist = (d.location.x - fx) ** 2 + (d.location.y - fy) ** 2
                if best is None or dist < best_dist:
                    best = d
                    best_dist = dist

            if best is None:
                break

            # Assign this drone to protect this field
            environment.assign_group(best, f"protecting {f.id}")
            assigned.add(best)
            needs[f.id] -= 1

        # Phase 3: Idle all drones not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")