from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Pre-compute field centers
        field_centers = {}
        for f in fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Count currently protecting drones per field
        protecting_counts = {f.id: 0 for f in fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                if fid in protecting_counts:
                    protecting_counts[fid] += 1

        # Prepare assignment tracking (use drone objects as keys)
        assigned = {}

        # Sort fields by threat level (descending)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Helper: squared distance from drone to field center
        def dist2_to_field(drone, center):
            dx = drone.location.x - center[0]
            dy = drone.location.y - center[1]
            return dx*dx + dy*dy

        # Step 1 and 2: Fill fields to full protection in threat order, using closest drones
        for field in fields_sorted:
            target_group = f"protecting {field.id}"
            current = protecting_counts.get(field.id, 0)
            needed = getattr(field, "drones_for_full_protection", 0) - current
            if needed <= 0:
                continue

            center = field_centers[field.id]

            # Build candidate pool: drones not already assigned, and not already protecting this field
            candidates = []
            for d in components:
                if d in assigned:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    # Already protecting this field; we will re-assign to the same group later to satisfy explicit reassignment
                    continue
                candidates.append(d)

            # Prefer closest drones
            candidates.sort(key=lambda dr: dist2_to_field(dr, center))

            to_take = min(needed, len(candidates))
            for i in range(to_take):
                drone = candidates[i]
                environment.assign_group(drone, target_group)
                assigned[drone] = target_group
                protecting_counts[field.id] = protecting_counts.get(field.id, 0) + 1

        # Step 2 (continued): If there are still drones and some fields are not fully protected,
        # allocate remaining drones to next highest-threat fields (closest first)
        for field in fields_sorted:
            target_group = f"protecting {field.id}"
            current = protecting_counts.get(field.id, 0)
            needed = getattr(field, "drones_for_full_protection", 0) - current
            if needed <= 0:
                continue

            center = field_centers[field.id]

            candidates = []
            for d in components:
                if d in assigned:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    continue
                candidates.append(d)

            candidates.sort(key=lambda dr: dist2_to_field(dr, center))
            to_take = min(needed, len(candidates))
            for i in range(to_take):
                drone = candidates[i]
                environment.assign_group(drone, target_group)
                assigned[drone] = target_group
                protecting_counts[field.id] = protecting_counts.get(field.id, 0) + 1

        # Final pass: re-assign everything else to a valid group
        for d in components:
            if d in assigned:
                # Already assigned by our plan; re-assign to the same group to satisfy the "explicit reassignment" rule
                current_group = assigned[d]
                environment.assign_group(d, current_group)
                continue

            # If drone is currently protecting something, re-assign to its current protection group
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                current_group = f"protecting {d.target_id}"
            else:
                current_group = "idle"

            environment.assign_group(d, current_group)
            assigned[d] = current_group