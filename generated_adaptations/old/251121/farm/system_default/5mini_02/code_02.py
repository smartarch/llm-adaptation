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