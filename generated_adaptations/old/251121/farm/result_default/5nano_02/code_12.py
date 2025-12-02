import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center_of_field(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _safe_group(self, name, group_ids):
        # If the requested group exists, use it; otherwise fall back to a safe default
        if name in group_ids:
            return name
        if "idle" in group_ids:
            return "idle"
        return group_ids[0] if group_ids else "idle"

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Allocation strategy:
        - Preserve existing protections by re-assigning current protectors to their
          corresponding "protecting {field.id}" groups.
        - Use idle drones to top-off protection for the fields with positive threat,
          prioritizing fields by threat level (desc) and filling up to each field's
          capacity (drones_for_full_protection - current_protectors).
        - Use the closest idle drones to each field to minimize travel time.
        - Any remaining drones are assigned to idle.
        """
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat fields, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, self._safe_group("idle", group_ids))
            return

        # Precompute current protectors by field
        current_by_field = {}
        for f in fields:
            current_by_field[f.id] = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
            ]

        # Step 1: Re-assign current protectors to their respective groups
        for f in fields:
            grp = self._safe_group(f"protecting {f.id}", group_ids)
            for d in current_by_field.get(f.id, []):
                environment.assign_group(d, grp)

        # Step 2: Build pool of idle (non-protecting) drones
        idle_pool = [d for d in components if getattr(d, "state", None) != "protecting"]

        # Step 3: Compute needs (capacities) for each field
        needs = []
        for f in fields:
            current = len(current_by_field.get(f.id, []))
            cap = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current)
            if cap > 0:
                needs.append((f, cap))

        # Step 4: Allocate idle drones to fields in threat-descending order
        needs.sort(key=lambda t: getattr(t[0], "threat_level", 0), reverse=True)

        assigned = set(d for lst in current_by_field.values() for d in lst)

        for f, cap in needs:
            if cap <= 0 or not idle_pool:
                continue
            center = self._center_of_field(f)

            def dist_to_field(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - center[0]
                    dy = loc.y - center[1]
                    return (dx*dx + dy*dy) ** 0.5
                return float("inf")

            idle_pool.sort(key=dist_to_field)
            take = min(cap, len(idle_pool))
            for i in range(take):
                d = idle_pool[i]
                environment.assign_group(d, self._safe_group(f"protecting {f.id}", group_ids))
                assigned.add(d)
            idle_pool = [d for d in idle_pool if d not in assigned]

        # Step 5: Assign any remaining drones to idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, self._safe_group("idle", group_ids))