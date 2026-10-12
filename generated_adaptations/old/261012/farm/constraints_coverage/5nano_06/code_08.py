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
        protecting_set = set(current_protectors)

        # Step A: fill to full protection if needed
        if len(current_protectors) < needed:
            center_x = (top_field.left + top_field.right) / 2.0
            center_y = (top_field.top + top_field.bottom) / 2.0

            def dist2_to_top(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx*dx + dy*dy

            candidates = [d for d in components if d not in protecting_set]
            candidates.sort(key=dist2_to_top)

            to_add = needed - len(current_protectors)
            for d in candidates[:to_add]:
                protecting_set.add(d)

        # Step B: ensure at least half of drones are protecting
        total_drones = len(components)
        half_target = (total_drones + 1) // 2
        if len(protecting_set) < half_target:
            center_x = (top_field.left + top_field.right) / 2.0
            center_y = (top_field.top + top_field.bottom) / 2.0

            def dist2_to_top(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx*dx + dy*dy

            candidates = [d for d in components if d not in protecting_set]
            candidates.sort(key=dist2_to_top)

            deficit = half_target - len(protecting_set)
            for d in candidates[:deficit]:
                protecting_set.add(d)

        # Final assignment: every drone gets exactly one group
        for d in components:
            if d in protecting_set:
                environment.assign_group(d, f"protecting {top_field.id}")
            else:
                environment.assign_group(d, "idle")