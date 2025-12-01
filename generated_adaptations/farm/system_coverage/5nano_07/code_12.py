from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Identify fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threat fields: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (highest first)
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = fields[0]

        # Precompute centers for quick distance calculations
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}

        # Helper to compute distance squared from a drone to a field center
        def dist2_to_field(drone, field_id):
            cx, cy = centers[field_id]
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # Final group assignment per drone
        final_group_for = {c: None for c in components}

        # Step 1: Top field protection using only idle drones
        current_top = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id)
        deficit_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0) - current_top))

        # Preserve existing protectors on the top field
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                final_group_for[c] = f"protecting {top_field.id}"

        if deficit_top > 0:
            pool = [c for c in components if getattr(c, "state", None) != "protecting"]  # only idle/detached drones
            pool.sort(key=lambda d: dist2_to_field(d, top_field.id))
            for c in pool[:deficit_top]:
                final_group_for[c] = f"protecting {top_field.id}"

        # Step 2: Allocate remaining idle drones to other fields (in threat order)
        # Compute needs for all fields
        needs = {}
        for f in fields:
            current = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id)
            needs[f.id] = max(0, int(getattr(f, "drones_for_full_protection", 0) - current))

        # Ensure top field deficit is accounted (in case we couldn't fill it fully above)
        top_final = sum(1 for c in components if final_group_for.get(c) == f"protecting {top_field.id}")
        if top_final < top_field.drones_for_full_protection:
            needs[top_field.id] = max(needs[top_field.id], int(top_field.drones_for_full_protection - top_final))

        # Idle pool excluding those already assigned to top field
        idle = [c for c in components if final_group_for.get(c) is None and getattr(c, "state", None) != "protecting"]

        # Fill deficits for other fields in threat order
        for f in fields[1:]:
            deficit = needs.get(f.id, 0)
            if deficit <= 0:
                continue
            center = centers[f.id]
            idle.sort(key=lambda d: dist2_to_field(d, f.id))
            chosen = idle[:deficit]
            for drone in chosen:
                final_group_for[drone] = f"protecting {f.id}"
            idle = idle[deficit:]

        # Step 3: Assign final groups to all drones
        for c in components:
            grp = final_group_for.get(c)
            if grp is None:
                grp = "idle"
            environment.assign_group(c, grp)