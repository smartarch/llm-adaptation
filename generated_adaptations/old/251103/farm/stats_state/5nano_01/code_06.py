import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Enhanced adaptive drone assignment strategy:

        - Primary objective: ensure the top-threat field is fully protected using the closest drones.
        - After securing the top field, allocate any remaining drones to other threatening fields to improve overall protection.
        - Minimize movement: prefer drones that are already near the top field or already en route to it.
        - Any drones not needed for protection are assigned to idle.

        This version distributes spare drones to other threatening fields in order of threat level.
        """
        # 1) Identify threatening fields (threat_level > 0)
        threatening_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatening_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Pick the top-threat field
        top_field = max(threatening_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_group = f"protecting {top_field.id}"

        # Track drones already assigned to avoid reassigning
        assigned_ids = set()

        # 3) Reassign drones already targeting the top field to the top group
        for d in components:
            if getattr(d, "target_id", None) == top_field.id:
                environment.assign_group(d, top_group)
                assigned_ids.add(id(d))

        # 4) Compute how many drones are needed to reach full protection for the top field
        drones_for_full = getattr(top_field, "drones_for_full_protection", 0)
        protecting = getattr(top_field, "protecting_drones", 0)
        arriving = sum(1 for d in components
                       if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id)
        needed_more = max(0, drones_for_full - (protecting + arriving))

        # 5) If more drones are needed, assign the closest available drones to the top field
        if needed_more > 0:
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            def dist2_to_top(drone):
                lx = getattr(drone.location, "x", 0.0)
                ly = getattr(drone.location, "y", 0.0)
                dx = lx - cx
                dy = ly - cy
                return dx * dx + dy * dy

            candidates = [d for d in components if id(d) not in assigned_ids and getattr(d, "target_id", None) != top_field.id]
            candidates.sort(key=dist2_to_top)

            for i in range(min(needed_more, len(candidates))):
                environment.assign_group(candidates[i], top_group)
                assigned_ids.add(id(candidates[i]))

        # 6) Distribute remaining drones to other threatening fields (to improve protection)
        other_fields = [f for f in threatening_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Prepare spare drones (not yet assigned to top field)
        spare = [d for d in components if id(d) not in assigned_ids and getattr(d, "target_id", None) != top_field.id]

        for field in other_fields:
            # Compute deficit for this field
            f_deficit = max(0, getattr(field, "drones_for_full_protection", 0) - (
                getattr(field, "protecting_drones", 0) +
                sum(1 for d in components if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == field.id)
            ))
            if f_deficit <= 0:
                continue

            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0

            def dist2_to_field(drone):
                lx = getattr(drone.location, "x", 0.0)
                ly = getattr(drone.location, "y", 0.0)
                dx = lx - cx
                dy = ly - cy
                return dx * dx + dy * dy

            spare.sort(key=dist2_to_field)

            i = 0
            while f_deficit > 0 and i < len(spare):
                d = spare[i]
                environment.assign_group(d, f"protecting {field.id}")
                assigned_ids.add(id(d))
                f_deficit -= 1
                i += 1
            spare = spare[i:]  # remove assigned drones from spare pool

        # 7) Idle any remaining drones
        for d in components:
            if id(d) in assigned_ids:
                continue
            if getattr(d, "target_id", None) == top_field.id:
                # Should already be in top_group; ensure it's grouped
                environment.assign_group(d, top_group)
                assigned_ids.add(id(d))
            else:
                environment.assign_group(d, "idle")