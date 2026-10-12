from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Total number of drones
        total_drones = len(components)

        # Gather fields with positive threat level and a positive protection requirement
        threat_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0 and getattr(f, "drones_for_full_protection", 0) > 0
        ]

        # If no threat, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Compute efficiency: threat_level / drones_for_full_protection
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (getattr(f, "threat_level", 0) / max(1, getattr(f, "drones_for_full_protection", 1))),
            reverse=True
        )

        # Greedy selection: pick fields to fully protect until we exhaust drones
        capacity = total_drones
        selected_fields = []
        for f in threat_fields_sorted:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            if needed <= 0:
                continue
            if capacity >= needed:
                selected_fields.append(f)
                capacity -= needed

        # If nothing selected (possible if all have high costs), we still try to protect the single top field
        if not selected_fields and threat_fields_sorted:
            f = threat_fields_sorted[0]
            selected_fields = [f]

        # Allocate drones to the selected fields: assign closest available drones to each field center
        assigned_group = {}  # drone_index -> group_id
        allocated = set()

        # Process selected fields in order of threat_level (most important first)
        for f in sorted(selected_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            center = center_of(f)
            center_x, center_y = center
            needed = int(getattr(f, "drones_for_full_protection", 0))

            # If no needed, skip
            if needed <= 0:
                continue

            # Gather unallocated drones with their distance to this center
            candidates = []
            for idx, d in enumerate(components):
                if idx in allocated:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = loc.x - center_x
                    dy = loc.y - center_y
                    dist = (dx * dx + dy * dy) ** 0.5
                candidates.append((dist, idx))

            candidates.sort()
            take = min(needed, len(candidates))
            for i in range(take):
                idx = candidates[i][1]
                assigned_group[idx] = f"protecting {f.id}"
                allocated.add(idx)

        # Any remaining drones become idle
        for idx, d in enumerate(components):
            if idx in assigned_group:
                environment.assign_group(d, assigned_group[idx])
            else:
                environment.assign_group(d, "idle")