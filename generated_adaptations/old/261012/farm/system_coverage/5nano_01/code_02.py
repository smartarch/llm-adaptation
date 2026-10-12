from typing import List
import math

# The base class is assumed to be importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Pick the top field by threat (tie-breaker by id to be deterministic)
        top_field = None
        if threat_fields:
            threat_fields_sorted = sorted(threat_fields, key=lambda f: (-f.threat_level, f.id))
            top_field = threat_fields_sorted[0]

        assignments = {}  # component -> group_id

        # If there is a top field, compute its protection needs
        if top_field is not None:
            top_group = f"protecting {top_field.id}"
            # Count current protectors for the top field (from simulation state)
            current_protectors = [c for c in components
                                  if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id]
            current_protectors_count = len(current_protectors)

            required = getattr(top_field, "drones_for_full_protection", 0)

            # Always assign existing protectors to the top field's protection group
            for c in current_protectors:
                assignments[c] = top_group

            # If more drones are needed, pick closest idle drones to the field center
            needed = max(0, int(required) - int(current_protectors_count))

            if needed > 0:
                # Compute field center
                cx = (top_field.left + top_field.right) / 2.0
                cy = (top_field.top + top_field.bottom) / 2.0

                # Gather idle drones
                idle_drones = [c for c in components if getattr(c, "state", None) == "idle"]

                # Sort idle drones by squared distance to field center
                def dist2(drone):
                    loc = getattr(drone, "location", None)
                    if loc is None:
                        return float("inf")
                    dx = loc.x - cx
                    dy = loc.y - cy
                    return dx*dx + dy*dy

                idle_drones_sorted = sorted(idle_drones, key=lambda d: dist2(d))

                for i in range(min(needed, len(idle_drones_sorted))):
                    c = idle_drones_sorted[i]
                    assignments[c] = top_group

        # Step 2: Assign the rest
        for c in components:
            if c in assignments:
                continue

            t_id = getattr(c, "target_id", None)
            st = getattr(c, "state", None)

            # If drone is currently targeting/protecting a field that still exists with threat, try to keep it there
            assigned = False
            if t_id is not None:
                # Only assign to a valid group if that field currently has threat > 0
                field_valid = any(getattr(f, "id", None) == t_id and getattr(f, "threat_level", 0) > 0 for f in environment.fields)
                if field_valid:
                    group = f"protecting {t_id}"
                    assignments[c] = group
                    assigned = True

            if not assigned:
                # If no valid field to protect, keep idle
                assignments[c] = "idle"

        # Apply group assignments
        for comp, group_id in assignments.items():
            environment.assign_group(comp, group_id)