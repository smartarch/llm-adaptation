Reasoning and adaptation strategy

We must always ensure the single field with the highest bird threat_level (if any with threat_level > 0) is fully protected using the closest available drones. Protecting means assigning the required number of drones (field.drones_for_full_protection) to that field's protecting group. Drones already assigned to that field — both those actively "protecting" and those "moving_to_field" with target_id equal to that field — should be counted toward the required number and kept assigned there. If that count is insufficient, fill up the remainder with the closest drones (by Euclidean distance to the field center) that are not already targeting that field. All other drones are placed in the "idle" group.

Tie-breaking and deterministic behavior:
- If multiple fields share the same top threat_level, pick the field with the lexicographically smallest id to be deterministic.
- If more drones are already assigned to the top field than required, leave them there (we do not forcibly reassign extras away).

Implementation notes:
- Compute each field's center using (left+right)/2, (top+bottom)/2 and compute distances from drone locations to that center.
- Use environment.assign_group(component, group_id) to perform assignments.
- If no field has threat_level > 0, assign all drones to "idle".
- Group name used for protection is exactly "protecting {field.id}" and must be one of the provided group_ids (if not found, fall back to "idle").

Below is the implementation as a Python class named SmartFarmAdaptation derived from the provided FarmAdaptation base class.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance_to_field(self, component, field):
        cx, cy = self._field_center(field)
        dx = component.location.x - cx
        dy = component.location.y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect candidate fields with positive threat
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, assign all drones to idle
        if not candidate_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Choose the field with highest threat_level; break ties by lexicographic field.id
        max_threat = max(f.threat_level for f in candidate_fields)
        top_fields = [f for f in candidate_fields if f.threat_level == max_threat]
        # deterministic tie-break:
        top_field = sorted(top_fields, key=lambda f: f.id)[0]

        protect_group = f"protecting {top_field.id}"
        if protect_group not in group_ids:
            # safety fallback
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        required = int(getattr(top_field, "drones_for_full_protection", 0))

        # Identify components already targeting this field (either moving_to_field or protecting)
        already_targeting = []
        others = []
        for comp in components:
            if getattr(comp, "target_id", None) == top_field.id and getattr(comp, "state", None) in ("moving_to_field", "protecting"):
                already_targeting.append(comp)
            else:
                others.append(comp)

        # Select drones: start with those already targeting (keep them)
        selected = list(already_targeting)

        # If we need more, choose closest drones from others
        if len(selected) < required:
            # sort remaining by distance to field center
            others_sorted = sorted(others, key=lambda c: self._distance_to_field(c, top_field))
            need = required - len(selected)
            selected.extend(others_sorted[:need])

        # Assign groups: selected -> protecting top_field, all others -> idle
        selected_set = set(selected)
        for comp in components:
            if comp in selected_set:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, "idle")
```