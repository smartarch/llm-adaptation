from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]

        # Pre-compute field centers and required drones for full protection
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in threat_fields}
        needs = {f.id: int(getattr(f, "drones_for_full_protection", len(components))) for f in threat_fields}

        # Build a single target plan for every drone
        target_group = {d: None for d in components}
        assigned = set()

        # Helper for distance to a field center
        def dist2_to_field(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, "x", 0) - cx
            dy = getattr(loc, "y", 0) - cy
            return dx * dx + dy * dy

        # Allocate protection for fields in order of threat
        for f in threat_fields:
            fid = f.id
            needed = needs[fid]

            # Current protectors for this field
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            for d in current:
                target_group[d] = f"protecting {fid}"
                assigned.add(d)

            to_allocate = max(0, needed - len(current))
            if to_allocate > 0:
                cx, cy = centers[fid]
                candidates = [d for d in components if d not in assigned]
                candidates.sort(key=lambda d: dist2_to_field(d, cx, cy))

                for d in candidates[:to_allocate]:
                    target_group[d] = f"protecting {fid}"
                    assigned.add(d)

        # Assign remaining drones to idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Ensure at least half of drones are protecting (fallback if needed)
        protecting_list = [d for d in components if target_group[d].startswith("protecting")]
        if len(protecting_list) < (len(components) + 1) // 2:
            deficit = (len(components) + 1) // 2 - len(protecting_list)
            # Use idle drones to boost protection of the top field
            idle_candidates = [d for d in components if target_group[d] == "idle"]
            top_cx, top_cy = centers[top_field.id]
            idle_candidates.sort(key=lambda d: dist2_to_field(d, top_cx, top_cy))

            for d in idle_candidates[:deficit]:
                target_group[d] = f"protecting {top_field.id}"
                protecting_list.append(d)

        # Final assignment: exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])