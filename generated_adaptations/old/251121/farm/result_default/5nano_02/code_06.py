import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center_of_field(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Allocate drones into groups to protect fields.
        - Top field (highest threat): fully protect using closest idle drones.
        - Remaining fields: allocate remaining idle drones to start protecting them,
          in order of threat level.
        - All drones are explicitly assigned to a group (idle or protecting a field).
        """
        # Helper to pick a valid group name
        def safe_group(name):
            # If the requested group exists, use it; otherwise fall back to idle or a valid default
            if name in group_ids:
                return name
            if "idle" in group_ids:
                return "idle"
            return group_ids[0] if group_ids else "idle"

        # Fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threat fields: set all drones to idle (or the first valid group)
            for d in components:
                environment.assign_group(d, safe_group("idle"))
            return

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = fields_sorted[0]
        top_group = safe_group(f"protecting {top_field.id}")

        top_center = self._center_of_field(top_field)
        needed_top = int(getattr(top_field, "drones_for_full_protection", 0))

        assigned = set()

        # Keep existing protectors for the top field
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                environment.assign_group(d, top_group)
                assigned.add(d)

        # Count current protectors on top
        current_top = [d for d in components if d in assigned]
        current_top_count = len(current_top)

        # Fill top field using idle drones
        if needed_top > current_top_count:
            # collect idle drones
            idle_candidates = []
            for d in components:
                if d in assigned:
                    continue
                if getattr(d, "state", None) == "idle":
                    loc = getattr(d, "location", None)
                    if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                        dx = loc.x - top_center[0]
                        dy = loc.y - top_center[1]
                        dist = (dx*dx + dy*dy)**0.5
                    else:
                        dist = float("inf")
                    idle_candidates.append((dist, d))
            idle_candidates.sort(key=lambda t: t[0])
            need = min(needed_top - current_top_count, len(idle_candidates))
            for i in range(need):
                d = idle_candidates[i][1]
                environment.assign_group(d, top_group)
                assigned.add(d)

        # Now allocate remaining idle drones to other high-threat fields
        remaining_idle = [d for d in components if d not in assigned and getattr(d, "state", None) == "idle"]
        # In order of threat
        for field in fields_sorted[1:]:
            needed = int(getattr(field, "drones_for_full_protection", 0))
            # current protectors for this field
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id]
            current_count = len(current)
            if needed <= current_count:
                continue
            slots = needed - current_count
            if not remaining_idle:
                continue
            center = self._center_of_field(field)

            def dist_to_field(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - center[0]
                    dy = loc.y - center[1]
                    return (dx*dx + dy*dy)**0.5
                return float("inf")

            remaining_idle.sort(key=dist_to_field)
            to_take = min(slots, len(remaining_idle))
            for i in range(to_take):
                d = remaining_idle[i]
                grp = safe_group(f"protecting {field.id}")
                environment.assign_group(d, grp)
                assigned.add(d)
            # Update remaining after assignments
            remaining_idle = [d for d in remaining_idle if d not in assigned]

        # Finally, assign any drones still unassigned to idle (or first valid group)
        for d in components:
            if d not in assigned:
                environment.assign_group(d, safe_group("idle"))