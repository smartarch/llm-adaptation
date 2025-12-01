from math import ceil, hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to assign safely (assumes group_id exists in group_ids per spec)
        def assign(c, gid):
            environment.assign_group(c, gid)

        # Find fields with positive threat level
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened field, send all drones to idle
        if not candidate_fields:
            for c in components:
                assign(c, "idle")
            return

        # Select the field with highest threat_level (tie-breaker: first encountered)
        highest = max(candidate_fields, key=lambda f: f.threat_level)

        # Required number of drones for full protection (round up if needed)
        required = int(ceil(getattr(highest, "drones_for_full_protection", 0)))
        if required <= 0:
            # Nothing to do for protection, idle all
            for c in components:
                assign(c, "idle")
            return

        # Compute field center for distance calculations
        fx = (highest.left + highest.right) / 2.0
        fy = (highest.top + highest.bottom) / 2.0

        # Identify current protectors for this field
        current_protectors = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == highest.id]

        # If already enough protectors, keep them; otherwise, select closest additional drones
        protectors_set = set(current_protectors)

        if len(current_protectors) < required:
            # Build list of candidate drones not already counted as protectors
            others = [c for c in components if c not in protectors_set]
            # Sort others by distance to field center
            others_sorted = sorted(others, key=lambda c: hypot(c.location.x - fx, c.location.y - fy))
            need = required - len(current_protectors)
            to_add = others_sorted[:need]
            for c in to_add:
                protectors_set.add(c)

        # Now assign groups: protectors -> protecting {field.id}, others -> idle
        protect_group = f"protecting {highest.id}"
        for c in components:
            if c in protectors_set:
                assign(c, protect_group)
            else:
                assign(c, "idle")