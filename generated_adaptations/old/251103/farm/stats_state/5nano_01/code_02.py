import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with threat level > 0
        threatening_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Always ensure there is at least an idle group
        top_group = "idle"  # default fallback
        top_field = None

        if not threatening_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(threatening_fields, key=lambda ff: getattr(ff, "threat_level", 0))
        top_group = f"protecting {top_field.id}"

        # Compute how many drones are currently protecting this field (based on target)
        current_protecting = [
            d for d in components if d.target_id == top_field.id
        ]  # includes any state (protecting, moving_to_field, etc.)
        current_protecting_count = len(current_protecting)

        # Drones already arriving to this field
        arriving_to_top = [
            d for d in components if d.state == "moving_to_field" and d.target_id == top_field.id
        ]
        arriving_count = len(arriving_to_top)

        # Drones needed for full protection
        drones_for_full = getattr(top_field, "drones_for_full_protection", 0)
        needed_more = max(0, drones_for_full - (getattr(top_field, "protecting_drones", 0) + arriving_count))

        # Center of the field for distance calculation
        center_x = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
        center_y = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

        # If there are drones currently targeting the top field, they should be in the top_group
        for d in current_protecting:
            environment.assign_group(d, top_group)

        # If we still need more drones, pick the closest from the rest
        if needed_more > 0:
            # Candidates are drones not already targeting the top field
            candidates = [d for d in components if d.target_id != top_field.id]
            # Compute squared distance to the field center
            def dist2(drone):
                lx = getattr(drone.location, "x", 0.0)
                ly = getattr(drone.location, "y", 0.0)
                dx = lx - center_x
                dy = ly - center_y
                return dx * dx + dy * dy

            candidates.sort(key=dist2)
            for i in range(min(needed_more, len(candidates))):
                environment.assign_group(candidates[i], top_group)

        # Finally, assign all remaining drones to idle (to satisfy "every component must be assigned to exactly one group")
        for d in components:
            # If this drone is already assigned to the top group via previous steps, skip reassigning
            if d.target_id == top_field.id:
                # It is already assigned to top_group above
                continue
            # If the drone was not assigned yet to the top group in this run, assign to idle
            environment.assign_group(d, "idle")