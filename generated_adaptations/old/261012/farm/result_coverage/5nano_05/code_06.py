from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No fields to protect; just idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Pre-compute field centers
        field_centers = {}
        for f in fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Count current protection for each field, counting both protecting and moving_to_field toward that field
        protecting_counts = {f.id: 0 for f in fields}
        field_ids = {f.id for f in fields}
        for d in components:
            fid = getattr(d, "target_id", None)
            state = getattr(d, "state", None)
            if fid in field_ids and state in ("protecting", "moving_to_field"):
                protecting_counts[fid] += 1

        # Track assignments we will make in this step
        assignments = {}

        # Sort fields by threat level (descending)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Helper: squared distance from drone to field center
        def dist2_to_field(drone, center):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return dx*dx + dy*dy

        # Step: attempt to fully protect the top field, using only idle drones and drones already heading to that field
        top_field = fields_sorted[0]
        top_id = top_field.id
        center_top = field_centers[top_id]
        current_top = protecting_counts.get(top_id, 0)
        needed_top = getattr(top_field, "drones_for_full_protection", 0) - current_top
        if needed_top > 0:
            # Pool of candidate drones: idle drones or drones already moving_to_field toward the top field
            pool = []
            for d in components:
                if d in assignments:
                    continue
                state = getattr(d, "state", None)
                fid = getattr(d, "target_id", None)
                if state == "idle":
                    pool.append(d)
                elif state == "moving_to_field" and fid == top_id:
                    pool.append(d)
                # Do not take drones that are protecting another field
            # Sort by closeness to top field
            pool.sort(key=lambda dr: dist2_to_field(dr, center_top))
            to_take = min(needed_top, len(pool))
            for i in range(to_take):
                drone = pool[i]
                environment.assign_group(drone, f"protecting {top_id}")
                assignments[drone] = f"protecting {top_id}"
                protecting_counts[top_id] = protecting_counts.get(top_id, 0) + 1

        # After attempting top field, optionally protect other fields using remaining idle drones
        # Recompute current protection including top field's updates
        # Note: we only use truly idle drones for other fields to minimize disruption
        # Build a list of idle drones (not yet assigned in this step)
        idle_drones = [d for d in components if d not in assignments and getattr(d, "state", None) == "idle"]

        for field in fields_sorted[1:]:
            fid = field.id
            center = field_centers[fid]
            current = protecting_counts.get(fid, 0)
            needed = getattr(field, "drones_for_full_protection", 0) - current
            if needed <= 0:
                continue

            pool = list(idle_drones)  # clone
            # Do not take drones that are heading to other fields (to avoid breaking others)
            pool = [d for d in pool if getattr(d, "target_id", None) is None]
            pool.sort(key=lambda dr: dist2_to_field(dr, center))
            to_take = min(needed, len(pool))
            for i in range(to_take):
                drone = pool[i]
                environment.assign_group(drone, f"protecting {fid}")
                assignments[drone] = f"protecting {fid}"
                idle_drones.remove(drone)
                protecting_counts[fid] = protecting_counts.get(fid, 0) + 1

        # Final pass: re-assign everything else to a valid group
        for d in components:
            if d in assignments:
                # Explicit reassignment to the chosen group
                environment.assign_group(d, assignments[d])
                continue

            # If drone is currently protecting or moving to a field, keep it in that protection group
            fid = getattr(d, "target_id", None)
            state = getattr(d, "state", None)
            if state in ("protecting", "moving_to_field") and fid is not None:
                current_group = f"protecting {fid}"
            else:
                current_group = "idle"

            environment.assign_group(d, current_group)