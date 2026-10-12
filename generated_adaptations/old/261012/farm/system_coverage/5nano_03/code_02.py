from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Find the field with the highest threat level > 0
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No field needs protection; idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        top_field = max(threat_fields, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"

        # 2) Re-assign drones already protecting the top field to the correct group
        assigned_ids = set()
        current_top_protectors = 0
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                environment.assign_group(c, top_group)
                assigned_ids.add(id(c))
                current_top_protectors += 1
        # 3) Compute how many more drones are needed for full protection
        needed = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protectors)

        # 4) If more drones are needed, pick the closest non-top-field drones to fill the gap
        if needed > 0:
            # Field center for distance calculation
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            candidates = []
            for c in components:
                if id(c) in assigned_ids:
                    continue
                loc = getattr(c, "location", None)
                dist = float("inf")
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
                candidates.append((dist, c))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                _, drone = candidates[i]
                environment.assign_group(drone, top_group)
                assigned_ids.add(id(drone))

        # 5) Remaining drones go idle
        for c in components:
            if id(c) not in assigned_ids:
                environment.assign_group(c, "idle")