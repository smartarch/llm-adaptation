import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, 'threat_level', 0) > 0]

        plan = {}  # drone -> target_group (exactly one assignment per drone)

        if not fields:
            # No threat: idle all drones
            for d in components:
                plan[d] = "idle"
        else:
            # Sort fields by threat level descending to pick the top field
            fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)
            top_field = fields_sorted[0]
            top_id = top_field.id

            # Current protection on the top field
            current_top = 0
            for d in components:
                if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == top_id:
                    current_top += 1

            required_top = int(getattr(top_field, 'drones_for_full_protection', 0))
            deficit = max(0, required_top - current_top)

            # Gather idle drones (prefer to move idle drones only)
            idle_drones = [d for d in components if getattr(d, 'state', None) == 'idle']

            # Assign closest idle drones to protect the top field
            if deficit > 0 and idle_drones:
                # Compute center of the top field
                cx = (top_field.left + top_field.right) / 2.0
                cy = (top_field.top + top_field.bottom) / 2.0

                # Distances to top field center
                idle_dists = []
                for d in idle_drones:
                    loc = getattr(d, 'location', None)
                    if loc is None:
                        dist = float('inf')
                    else:
                        dx = getattr(loc, 'x', 0.0) - cx
                        dy = getattr(loc, 'y', 0.0) - cy
                        dist = math.hypot(dx, dy)
                    idle_dists.append((dist, d))
                idle_dists.sort(key=lambda t: t[0])

                take = min(deficit, len(idle_dists))
                for i in range(take):
                    drone = idle_dists[i][1]
                    plan[drone] = f"protecting {top_id}"

            # For all drones not in plan, assign them to maintain current protection or idle
            for d in components:
                if d in plan:
                    continue
                # If the drone is currently protecting some field, keep protecting that field
                if getattr(d, 'state', None) == 'protecting':
                    gid = getattr(d, 'target_id', None)
                    plan[d] = f"protecting {gid}"
                else:
                    plan[d] = "idle"

        # Apply assignments (exactly one per drone)
        for d, grp in plan.items():
            environment.assign_group(d, grp)