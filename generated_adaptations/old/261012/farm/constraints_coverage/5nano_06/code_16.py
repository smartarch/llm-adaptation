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

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Drones needed for full protection for each field
        needs = {f.id: int(getattr(f, "drones_for_full_protection", len(components))) for f in threat_fields}

        # Build the target mapping: which group each drone should belong to
        target_group = {d: None for d in components}

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance squared from a drone to a field center
        def dist2_to(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # Step 0: mark existing protectors for all fields
        for f in threat_fields:
            fid = f.id
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            for d in current:
                target_group[d] = f"protecting {fid}"

        # Step 1: For each field, ensure it has exactly needs[fid] protectors
        for f in threat_fields:
            fid = f.id
            center_x, center_y = center_of(f)

            # Current protectors for this field according to target_group
            current_for_field = [d for d in components if target_group[d] == f"protecting {fid}"]
            current_count = len(current_for_field)

            # If too many, drop extras (farther from the field first)
            if current_count > needs[fid]:
                extras = current_count - needs[fid]
                current_for_field.sort(key=lambda d: dist2_to(d, center_x, center_y), reverse=True)
                for d in current_for_field[:extras]:
                    target_group[d] = None
                current_for_field = [d for d in components if target_group[d] == f"protecting {fid}"]
                current_count = len(current_for_field)

            # If too few, allocate closest available drones
            if current_count < needs[fid]:
                to_add = needs[fid] - current_count
                # Candidates are drones not currently protecting this field
                candidates = [d for d in components if target_group[d] != f"protecting {fid}"]
                candidates.sort(key=lambda d: dist2_to(d, center_x, center_y))
                for d in candidates[:to_add]:
                    target_group[d] = f"protecting {fid}"

        # Step 2: Any drone not assigned yet becomes idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Final assignment: exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])