import math
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with any threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(threat_fields, key=lambda f: f.threat_level)
        field_id = top_field.id

        # Compute how many drones are needed to reach full protection
        eff_prot = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        full_needed = getattr(top_field, "drones_for_full_protection", 0)
        need = max(0, full_needed - eff_prot)

        if need == 0:
            # Already fully protected: keep drones protecting this field, others idle
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                    environment.assign_group(d, f"protecting {field_id}")
                else:
                    environment.assign_group(d, "idle")
            return

        # Compute field center
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Keep drones already protecting this field
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                environment.assign_group(d, f"protecting {field_id}")

        # Build list of candidate drones (exclude those already protecting this field)
        candidates = []
        for d in components:
            if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id):
                loc = getattr(d, "location", None)
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)
                else:
                    dist = float('inf')
                candidates.append((dist, d))
        candidates.sort(key=lambda t: t[0])

        # Assign the closest drones to reinforce the top field
        to_assign = min(len(candidates), need)
        for i in range(to_assign):
            _, drone = candidates[i]
            environment.assign_group(drone, f"protecting {field_id}")

        # Remaining drones idle
        for dist, drone in candidates[to_assign:]:
            environment.assign_group(drone, "idle")