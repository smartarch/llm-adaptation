import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between drone and field center
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        idle_group = "idle"
        # Find fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            if idle_group in group_ids:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            else:
                # Fallback: if idle not available, assign to first available group
                fallback = group_ids[0] if group_ids else None
                for comp in components:
                    if fallback:
                        environment.assign_group(comp, fallback)
            return

        # Choose the field with highest threat_level
        target_field = max(threatened_fields, key=lambda f: getattr(f, "threat_level", 0.0))
        protect_group = f"protecting {target_field.id}"

        # Ensure the protect group exists in group_ids; if not, fall back to idle for everyone
        if protect_group not in group_ids:
            if idle_group in group_ids:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            else:
                fallback = group_ids[0] if group_ids else None
                for comp in components:
                    if fallback:
                        environment.assign_group(comp, fallback)
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Identify drones already protecting this field
        selected = []
        for comp in components:
            if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == target_field.id:
                selected.append(comp)

        # If not enough, select closest drones among remaining to fill the requirement
        if len(selected) < required:
            needed = max(0, required - len(selected))
            remaining = [c for c in components if c not in selected]
            remaining.sort(key=lambda c: distance_to_field_center(c, target_field))
            to_add = remaining[:needed]
            selected.extend(to_add)

        # Assign selected drones to protecting group
        for comp in selected:
            environment.assign_group(comp, protect_group)

        # Assign all other drones to idle (or fallback if idle not present)
        for comp in components:
            if comp in selected:
                continue
            if idle_group in group_ids:
                environment.assign_group(comp, idle_group)
            else:
                # fallback to first available group id if idle missing
                fallback = group_ids[0] if group_ids else None
                if fallback:
                    environment.assign_group(comp, fallback)