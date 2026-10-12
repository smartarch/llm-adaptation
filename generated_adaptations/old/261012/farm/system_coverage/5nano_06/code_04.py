from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Prepare a map of final groups for each field
        final_groups = {f"protecting {f.id}": set() for f in fields_sorted}

        # First, map currently protecting drones to their groups
        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st == "protecting" and tid is not None:
                gid = f"protecting {tid}"
                if gid in final_groups:
                    final_groups[gid].add(d)

        # Greedily fill each field to full using closest available drones
        assigned = set().union(*final_groups.values())
        for idx, field in enumerate(fields_sorted):
            gid = f"protecting {field.id}"
            current = final_groups[gid]
            needed = int(getattr(field, "drones_for_full_protection", 0))
            if len(current) >= max(needed, 0):
                continue
            need = max(needed, 0) - len(current)

            cx = (getattr(field, "left") + getattr(field, "right")) / 2.0
            cy = (getattr(field, "top") + getattr(field, "bottom")) / 2.0

            def distance(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                x = getattr(loc, "x", 0.0)
                y = getattr(loc, "y", 0.0)
                return math.hypot(x - cx, y - cy)

            # Candidates are drones not already assigned to any final group
            candidates = [d for d in components if d not in assigned]
            candidates.sort(key=distance)

            for d in candidates:
                if len(current) >= max(needed, 0) or need <= 0:
                    break
                current.add(d)
                assigned.add(d)

        # Build a mapping from drone to its final group
        drone_to_group = {}
        for gid, drones in final_groups.items():
            for d in drones:
                drone_to_group[d] = gid

        # Assign each drone to its final group; default to idle if not assigned
        for d in components:
            if d in drone_to_group:
                environment.assign_group(d, drone_to_group[d])
            else:
                environment.assign_group(d, "idle")