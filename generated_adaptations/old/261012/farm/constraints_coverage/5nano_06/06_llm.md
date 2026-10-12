Reasoning and updated adaptation strategy

Root cause of the failure:
- The tests require that the fleet focuses on fully protecting the single most threatened field before considering other fields. Partial protection of multiple fields is discouraged.
- Drones protecting the most threatened field must be the closest available drones.
- Each drone must be assigned exactly once in a single pass.

Updated strategy:
- Identify the single most threatened field (highest threat_level > 0).
- Compute how many drones are needed for full protection of that field (top_drones_needed).
- Determine how many drones are already protecting that field (current_protectors).
- If current_protectors >= needed: assign those drones to the protecting group for that field and all others to idle.
- Otherwise, select the closest drones to the field center among the not-yet-protecting drones to reach the needed count, and assign them to protect the top field.
- All remaining drones get assigned to idle.
- This ensures:
  - The top field is always fully protected when possible.
  - The drones protecting it are the closest ones.
  - No partial protection of other fields occurs unless the top field is fully protected (in which case the policy can be extended, but tests expect the top-field-first behavior).

Python code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Select the most threatened field
        top_field = max(threat_fields, key=lambda f: f.threat_level)

        # Drones needed for full protection of the top field
        needed = int(getattr(top_field, "drones_for_full_protection", len(components)))

        # Current drones protecting the top field
        current_protectors = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        current_count = len(current_protectors)

        # If already fully protected, assign those drones to protection group and others idle
        if current_count >= needed:
            for d in components:
                if d in current_protectors:
                    environment.assign_group(d, f"protecting {top_field.id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Compute center of the top field
        top_center_x = (top_field.left + top_field.right) / 2.0
        top_center_y = (top_field.top + top_field.bottom) / 2.0

        def dist2_to_top(d):
            loc = getattr(d, "location", None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, "x", 0) - top_center_x
            dy = getattr(loc, "y", 0) - top_center_y
            return dx * dx + dy * dy

        # Candidates: drones not already protecting the top field
        candidates = [d for d in components if d not in current_protectors]

        # Sort candidates by proximity to the top field center
        candidates.sort(key=dist2_to_top)

        to_add = needed - current_count
        assigned_to_top = set(current_protectors)

        for d in candidates[:to_add]:
            assigned_to_top.add(d)

        # Final assignment: top field protectors vs idle
        for d in components:
            if d in assigned_to_top:
                environment.assign_group(d, f"protecting {top_field.id}")
            else:
                environment.assign_group(d, "idle")
```