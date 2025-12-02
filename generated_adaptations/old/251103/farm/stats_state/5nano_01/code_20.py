from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Movement-conscious, multi-field protection with a simple, robust heuristic:

        Strategy goals:
        - Primary: fully protect the top-threat field (highest threat_level > 0) using the closest drones.
        - Minimize movement: reuse drones already targeting or near the top field; only move drones as needed to reach full protection.
        - After top field is protected, bolster other threatening fields in a measured way, preferring idle drones and those near the field center.
        - All drones not used for protection are idle.

        This approach avoids excessive thrashing and tries to keep drones near their targets to reduce moving_to_field overhead.
        """

        # 1) Identify threatening fields
        threatening_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Top-threat field
        top_field = max(threatening_fields, key=lambda f: getattr(f, "threat_level", 0))
        top_group = f"protecting {top_field.id}"

        assigned_ids = set()

        # 3) Reuse drones already targeting the top field
        for d in components:
            if getattr(d, "target_id", None) == top_field.id:
                environment.assign_group(d, top_group)
                assigned_ids.add(id(d))

        # 4) Compute how many drones are needed to reach full protection for the top field
        drones_for_full = getattr(top_field, "drones_for_full_protection", 0)
        protecting = getattr(top_field, "protecting_drones", 0)
        arriving = sum(
            1 for d in components
            if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id
        )
        needed_more = max(0, drones_for_full - (protecting + arriving))

        # 5) If more drones are needed, assign the closest available drones toward the top field
        if needed_more > 0:
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            def dist2_to_top(drone):
                lx = getattr(drone.location, "x", 0.0)
                ly = getattr(drone.location, "y", 0.0)
                dx = lx - cx
                dy = ly - cy
                return dx * dx + dy * dy

            candidates = [
                d for d in components
                if id(d) not in assigned_ids and getattr(d, "target_id", None) != top_field.id
            ]
            # Prefer idle drones first (to minimize disruption), then closest ones
            candidates.sort(key=lambda d: (getattr(d, "state", "") != "idle", dist2_to_top(d)))

            for i in range(min(needed_more, len(candidates))):
                environment.assign_group(candidates[i], top_group)
                assigned_ids.add(id(candidates[i]))

        # 6) After top field is handled, bolster other threatened fields with remaining drones
        other_fields = [f for f in threatening_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        spare = [d for d in components if id(d) not in assigned_ids and getattr(d, "target_id", None) != top_field.id]

        for field in other_fields:
            # Deficit for this field: drones needed to reach full protection
            arriving_to_field = sum(
                1 for d in components
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == field.id
            )
            f_deficit = max(0, getattr(field, "drones_for_full_protection", 0) - (
                getattr(field, "protecting_drones", 0) +
                getattr(field, "arriving_drones", 0) +
                arriving_to_field
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

            # Prefer idle drones first, then closest ones
            spare.sort(key=lambda d: (getattr(d, "state", "") != "idle", dist2_to_field(d)))

            i = 0
            while f_deficit > 0 and i < len(spare):
                d = spare[i]
                environment.assign_group(d, f"protecting {field.id}")
                assigned_ids.add(id(d))
                f_deficit -= 1
                i += 1
            spare = spare[i:]

        # 7) Idle any remaining drones
        for d in components:
            if id(d) in assigned_ids:
                continue
            if getattr(d, "target_id", None) == top_field.id:
                environment.assign_group(d, top_group)
                assigned_ids.add(id(d))
            else:
                environment.assign_group(d, "idle")