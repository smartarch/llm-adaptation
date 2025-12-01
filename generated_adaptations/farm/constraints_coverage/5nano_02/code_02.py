from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", [])
        fields_with_threat = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat (deterministic tie-breaker by first occurrence)
        target_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        target_id = getattr(target_field, "id")

        # Compute center of the target field
        left = getattr(target_field, "left", 0.0)
        right = getattr(target_field, "right", 0.0)
        top = getattr(target_field, "top", 0.0)
        bottom = getattr(target_field, "bottom", 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Drones currently protecting the target field
        current_protectors = [
            c for c in components
            if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == target_id
        ]
        current_count = len(current_protectors)

        # Drones required for full protection of the target field
        drones_for_full = getattr(target_field, "drones_for_full_protection", 0)
        needed = drones_for_full - current_count
        if needed < 0:
            needed = 0

        # Candidate drones: not already protecting the target
        candidates = [c for c in components if c not in current_protectors]

        # Sort candidates by distance to the target field center
        def distance_to_center(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - center_x
            dy = getattr(loc, "y", 0.0) - center_y
            return math.hypot(dx, dy)

        candidates_sorted = sorted(candidates, key=distance_to_center)

        # Pick up to 'needed' closest drones to join protection
        chosen_to_protect = set(candidates_sorted[:needed])

        protect_group = f"protecting {target_id}"

        # Re-assign groups: protect target_field with current_protectors + chosen drones; rest idle
        for c in components:
            if c in current_protectors or c in chosen_to_protect:
                environment.assign_group(c, protect_group)
            else:
                environment.assign_group(c, "idle")