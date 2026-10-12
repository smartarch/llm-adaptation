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
        top_field = threat_fields[0]

        # Drones needed for full protection for each field
        needs = {f.id: int(getattr(f, "drones_for_full_protection", len(components))) for f in threat_fields}

        # Build the target group map (one assignment per drone)
        target_group = {d: None for d in components}

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Step 0: mark existing protectors for all fields
        for f in threat_fields:
            fid = f.id
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            for d in current:
                target_group[d] = f"protecting {fid}"

        # Step 1: Ensure top field reaches its full protection quota (allow reallocations)
        top_needed = needs[top_field.id]
        current_top = [d for d in components if target_group[d] == f"protecting {top_field.id}"]
        current_top_count = len(current_top)

        if current_top_count < top_needed:
            center_x, center_y = center_of(top_field)

            def dist2_to_top(d, cx=center_x, cy=center_y):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float('inf')
                dx = loc.x - cx
                dy = loc.y - cy
                return dx*dx + dy*dy

            # Candidates include any drones not currently protecting the top field
            candidates = [d for d in components if target_group[d] != f"protecting {top_field.id}"]
            candidates.sort(key=dist2_to_top)

            to_add = top_needed - current_top_count
            for d in candidates[:to_add]:
                target_group[d] = f"protecting {top_field.id}"
                current_top.append(d)

        # Step 2: Ensure at least half of drones are protecting (prefer top field and propagate to others up to needs)
        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        def current_protecting_count():
            return sum(1 for d in components if target_group[d] is not None and target_group[d].startswith("protecting"))

        protecting_count = current_protecting_count()

        if protecting_count < half_target:
            # Try to fill needs across fields starting from the top field
            for f in threat_fields:
                fid = f.id
                current_for_field = sum(1 for d in components if target_group[d] == f"protecting {fid}")
                remaining = max(0, needs[fid] - current_for_field)
                if remaining <= 0:
                    continue

                cx, cy = center_of(f)

                def dist2_to_field_idle(drone, cx=cx, cy=cy):
                    loc = getattr(drone, "location", None)
                    if loc is None:
                        return float('inf')
                    dx = loc.x - cx
                    dy = loc.y - cy
                    return dx*dx + dy*dy

                # Allow reallocating from any drone not already protecting this field
                candidates = [d for d in components if target_group[d] != f"protecting {fid}"]
                candidates.sort(key=dist2_to_field_idle)

                for d in candidates[:remaining]:
                    target_group[d] = f"protecting {fid}"
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Step 3: Any drone not assigned yet becomes idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Final assignment: exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])