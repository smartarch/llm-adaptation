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
        - Top field (highest threat): fully protect using closest drones.
        - Remaining fields: allocate remaining drones to improve protection for other high-threat fields.
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

        # Current protectors for the top field
        current_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]

        assigned = {}

        # Keep current top-field protectors
        for d in current_top:
            assigned[d] = top_group
            environment.assign_group(d, top_group)

        # Pool of drones not currently protecting the top field
        pool = [
            d for d in components
            if d not in current_top and getattr(d, "state", None) != "protecting"
        ]

        # Fill up the top field to full protection using closest drones
        to_fill = max(0, needed_top - len(current_top))
        if to_fill > 0 and pool:
            def dist_to_top(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - top_center[0]
                    dy = loc.y - top_center[1]
                    return (dx * dx + dy * dy) ** 0.5
                return float("inf")

            pool.sort(key=dist_to_top)
            for i in range(min(to_fill, len(pool))):
                d = pool[i]
                assigned[d] = top_group
                environment.assign_group(d, top_group)

        # Remaining drones (not yet assigned) can help other fields
        remaining = [d for d in components if d not in assigned]
        others = fields_sorted[1:]

        for field in others:
            field_center = self._center_of_field(field)
            needed = int(getattr(field, "drones_for_full_protection", 0))

            # Current protectors for this field
            current = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id
            ]
            need = max(0, needed - len(current))
            if need <= 0:
                continue

            if not remaining:
                break

            def dist_to_field(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - field_center[0]
                    dy = loc.y - field_center[1]
                    return (dx * dx + dy * dy) ** 0.5
                return float("inf")

            remaining.sort(key=dist_to_field)
            add = min(need, len(remaining))
            for i in range(add):
                d = remaining[i]
                grp = safe_group(f"protecting {field.id}")
                assigned[d] = grp
                environment.assign_group(d, grp)

            # Remove assigned drones from remaining
            remaining = [d for d in remaining if d not in assigned]

        # Finally, assign any unassigned drones to idle (or first valid group if idle not available)
        for d in components:
            if d not in assigned:
                environment.assign_group(d, safe_group("idle"))