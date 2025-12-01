from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        target_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not target_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat level
        target_field = max(target_fields, key=lambda f: f.threat_level)
        group_name = f"protecting {target_field.id}"

        # Number of drones needed for full protection
        needed = int(getattr(target_field, "drones_for_full_protection", 0))
        if needed <= 0:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Center of the target field
        center_x = (target_field.left + target_field.right) / 2.0
        center_y = (target_field.top + target_field.bottom) / 2.0

        def dist_to_center(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            return ((loc.x - center_x) ** 2 + (loc.y - center_y) ** 2) ** 0.5

        # Drones currently protecting the target field
        current_protectors = [
            (idx, d)
            for idx, d in enumerate(components)
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == target_field.id
        ]

        # Keep the closest ones up to the needed amount
        current_protectors.sort(key=lambda t: dist_to_center(t[1]))
        keep_n = min(needed, len(current_protectors))
        keep_indices = set(idx for idx, _ in current_protectors[:keep_n])

        # Remaining drones to fill (if we have fewer than needed)
        remaining = max(0, needed - keep_n)

        # Candidates to fill from (excluding those we decided to keep)
        candidates = [
            (dist_to_center(d), idx, d)
            for idx, d in enumerate(components)
            if idx not in keep_indices
        ]
        candidates.sort(key=lambda t: t[0])

        fill_indices = set()
        for i in range(min(remaining, len(candidates))):
            fill_indices.add(candidates[i][1])

        # Assign groups: keep and fill go to the target protection group; others idle
        for idx, d in enumerate(components):
            if idx in keep_indices or idx in fill_indices:
                environment.assign_group(d, group_name)
            else:
                environment.assign_group(d, "idle")