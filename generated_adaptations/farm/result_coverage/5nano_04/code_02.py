from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Pick the top-threat field (largest threat_level)
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # 3) Compute field center
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        top_group = f"protecting {top_field.id}"

        # 4) Count current protectors for the top field
        current_protect_indices = [
            i for i, c in enumerate(components)
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id
        ]
        current_protect_count = len(current_protect_indices)

        # 5) Drones needed to fully protect top field
        # drones_for_full_protection is assumed to be an int-like value
        needed = int(getattr(top_field, "drones_for_full_protection", 0)) - current_protect_count
        if needed < 0:
            needed = 0

        assigned_to_top = set(current_protect_indices)

        # 6) If we need more drones, pick closest drones (not already protecting this field)
        if needed > 0:
            candidates = [i for i in range(len(components)) if i not in current_protect_indices]
            # Compute distance from drone to field center
            distances = []
            for i in candidates:
                loc = getattr(components[i], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    d = float("inf")
                else:
                    dx = loc.x - center_x
                    dy = loc.y - center_y
                    d = sqrt(dx*dx + dy*dy)
                distances.append((d, i))
            distances.sort(key=lambda t: t[0])

            # Take the closest 'needed' drones
            for _, idx in distances[:needed]:
                environment.assign_group(components[idx], top_group)
                assigned_to_top.add(idx)

        # 7) Assign all drones not in the top_group to idle
        for idx, drone in enumerate(components):
            if idx in assigned_to_top:
                # Ensure the explicit assignment to the top_group (even for existing holders)
                environment.assign_group(drone, top_group)
            else:
                environment.assign_group(drone, "idle")