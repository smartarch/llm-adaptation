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
        - Preserve all current protectors by re-assigning them to their respective "protecting {field.id}" groups.
        - Use idle (non-protecting) drones to top-off protection for the highest-threat field.
        - Use any remaining idle drones to bolster other high-threat fields in threat order.
        - Ensure every drone ends up in a valid group (idle or a protecting group).
        """
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat fields, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, self._safe_group("idle", group_ids))
            return

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = fields_sorted[0]
        top_group = self._safe_group(f"protecting {top_field.id}", group_ids)

        # Compute current protectors per field before any re-assignment
        current_protectors_by_field = {}
        for f in fields_sorted:
            current_protectors_by_field[f.id] = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
            ]

        assigned = set()

        # Step 1: Re-assign current protectors to their respective groups
        for f in fields_sorted:
            grp = self._safe_group(f"protecting {f.id}", group_ids)
            for d in current_protectors_by_field.get(f.id, []):
                environment.assign_group(d, grp)
                assigned.add(d)

        # Step 2: Build pool of drones available to protect (non-protecting drones)
        pool = [d for d in components if d not in assigned and getattr(d, "state", None) != "protecting"]

        # Step 3: Top field protection
        needed_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)) - len(current_protectors_by_field.get(top_field.id, [])))
        if needed_top > 0 and pool:
            top_center = self._center_of_field(top_field)

            def dist_to_top(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - top_center[0]
                    dy = loc.y - top_center[1]
                    return (dx*dx + dy*dy) ** 0.5
                return float("inf")

            pool.sort(key=dist_to_top)
            take = min(needed_top, len(pool))
            for i in range(take):
                d = pool[i]
                environment.assign_group(d, top_group)
                assigned.add(d)
            pool = [d for d in pool if d not in assigned]

        # Step 4: Use remaining idle drones to bolster other high-threat fields
        for f in fields_sorted[1:]:
            needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(current_protectors_by_field.get(f.id, [])))
            if needed <= 0 or not pool:
                continue

            center = self._center_of_field(f)

            def dist_to_field(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - center[0]
                    dy = loc.y - center[1]
                    return (dx*dx + dy*dy) ** 0.5
                return float("inf")

            pool.sort(key=dist_to_field)
            take = min(needed, len(pool))
            for i in range(take):
                d = pool[i]
                grp = self._safe_group(f"protecting {f.id}", group_ids)
                environment.assign_group(d, grp)
                assigned.add(d)
            pool = [d for d in pool if d not in assigned]

        # Step 5: Assign any remaining drones to idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, self._safe_group("idle", group_ids))