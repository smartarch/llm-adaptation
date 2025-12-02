from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat level (> 0)
        top_field = None
        for f in getattr(environment, 'fields', []):
            if getattr(f, 'threat_level', 0) > 0:
                if top_field is None or getattr(f, 'threat_level', 0) > getattr(top_field, 'threat_level', 0):
                    top_field = f

        # If there is no high-threat field, idle all drones
        if top_field is None:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Compute field center
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Count current drones protecting this field
        current_protecting = 0
        for c in components:
            if getattr(c, 'state', None) == 'protecting' and getattr(c, 'target_id', None) == top_field.id:
                current_protecting += 1

        drones_needed = getattr(top_field, 'drones_for_full_protection', 0)

        # If already fully protected, keep those drones there and idle the rest
        if current_protecting >= drones_needed:
            for c in components:
                if not (getattr(c, 'state', None) == 'protecting' and getattr(c, 'target_id', None) == top_field.id):
                    environment.assign_group(c, "idle")
            return

        # Need to allocate more drones to this field
        need = drones_needed - current_protecting

        # Build candidate list (exclude drones already protecting top_field)
        candidates = []
        for c in components:
            if not (getattr(c, 'state', None) == 'protecting' and getattr(c, 'target_id', None) == top_field.id):
                loc = getattr(c, 'location', None)
                if loc is None:
                    dist = float('inf')
                else:
                    dx = getattr(loc, 'x', 0) - cx
                    dy = getattr(loc, 'y', 0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, c))

        candidates.sort(key=lambda t: t[0])

        # Assign the nearest 'need' drones to protect the top field
        for i in range(min(need, len(candidates))):
            drone = candidates[i][1]
            environment.assign_group(drone, f"protecting {top_field.id}")

        # Set any remaining drones to idle
        for _, drone in candidates[min(need, len(candidates)) :]:
            environment.assign_group(drone, "idle")