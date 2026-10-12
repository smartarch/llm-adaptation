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

        # Build a map of target groups; we will assign each drone exactly once
        target_group = {d: None for d in components}

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Step 0: mark existing protectors for the top fields (if any)
        protecting_set = set()
        for f in threat_fields:
            fid = f.id
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            for d in current:
                target_group[d] = f"protecting {fid}"
                protecting_set.add(d)

        # Step 1: Ensure each field reaches its full protection quota in order (closest first)
        for f in threat_fields:
            fid = f.id
            needed = needs[fid]
            current_for_field = [d for d in components if target_group[d] == f"protecting {fid}"]
            current_count = len(current_for_field)

            if current_count >= needed:
                continue  # already full for this field

            center_x, center_y = center_of(f)

            def dist2_to_field(drone, cx=center_x, cy=center_y):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                dx = loc.x - cx
                dy = loc.y - cy
                return dx*dx + dy*dy

            candidates = [d for d in components if d not in protecting_set]
            candidates.sort(key=dist2_to_field)

            to_add = needed - current_count
            for d in candidates[:to_add]:
                target_group[d] = f"protecting {fid}"
                protecting_set.add(d)

        # Step 2: If fewer than half the drones are protecting, allocate additional closest idle drones
        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        def current_protecting_count():
            return sum(1 for d in components if target_group[d] is not None and target_group[d].startswith("protecting"))

        protecting_count = current_protecting_count()

        if protecting_count < half_target:
            # For each field (in threat order), try to fill up to its need from idle drones
            for f in threat_fields:
                fid = f.id
                current_for_field = sum(1 for d in components if target_group[d] == f"protecting {fid}")
                remaining = max(0, needs[fid] - current_for_field)
                if remaining <= 0:
                    continue

                center_x, center_y = center_of(f)

                def dist2_to_field_idle(drone, cx=center_x, cy=center_y):
                    loc = getattr(drone, "location", None)
                    if loc is None:
                        return float('inf')
                    dx = loc.x - cx
                    dy = loc.y - cy
                    return dx*dx + dy*dy

                idle_candidates = [d for d in components if target_group[d] is None]
                idle_candidates.sort(key=dist2_to_field_idle)

                for d in idle_candidates[:remaining]:
                    target_group[d] = f"protecting {fid}"
                    protecting_set.add(d)
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
            # If after trying to fill all fields we still haven't reached half, we simply leave as is (no more drones available)

        # Step 3: Any drone not assigned yet becomes idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Final assignment: exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])