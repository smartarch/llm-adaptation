from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Find the top-threat field
        top_field = None
        top_threat = -1.0
        for f in environment.fields:
            threat = getattr(f, "threat_level", 0.0)
            if threat > top_threat and threat > 0.0:
                top_threat = threat
                top_field = f

        # If no threatening field, idle all drones
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_group = f"protecting {top_field.id}"
        # Make sure the group exists in the provided list (defensive check)
        if top_group not in group_ids:
            # If for some reason the group isn't listed, fall back to idle for safety
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Step 2: Count current protectors for the top field
        current_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        current_count = len(current_protecting)

        # Drones required for full protection
        drones_needed = getattr(top_field, "drones_for_full_protection", len(components))
        if drones_needed <= 0:
            drones_needed = len(components)

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        field_center_pt = field_center(top_field)

        # If already fully protected, keep those drones in place, others idle
        if current_count >= drones_needed:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    environment.assign_group(d, top_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Step 3: Need to allocate more drones to top_field
        needed = int(drones_needed - current_count)
        # Build candidate list: drones not currently protecting top_field
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                # skip, these are already protecting top_field
                continue
            # Distance to field center
            loc = getattr(d, "location", None)
            if loc is None:
                dist = float('inf')
            else:
                dx = getattr(loc, "x", 0.0) - field_center_pt[0]
                dy = getattr(loc, "y", 0.0) - field_center_pt[1]
                dist = math.hypot(dx, dy)
            candidates.append((dist, d))

        candidates.sort(key=lambda t: t[0])
        chosen = [d for _, d in candidates[:needed]]

        # Step 4: Reassign groups
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                # Keep current protectors for top field
                environment.assign_group(d, top_group)
            elif d in chosen:
                # Assign the closest drones to protect top_field
                environment.assign_group(d, top_group)
            else:
                # All others idle
                environment.assign_group(d, "idle")