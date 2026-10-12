from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Pre-compute field centers
        field_centers = {}
        for f in fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        field_ids = {f.id for f in fields}

        # Count current protection for each field (protecting or moving_to_field toward that field)
        protecting_counts = {fid: 0 for fid in field_ids}
        for d in components:
            fid = getattr(d, "target_id", None)
            st = getattr(d, "state", None)
            if fid in field_ids and st in ("protecting", "moving_to_field"):
                protecting_counts[fid] += 1

        # Track assignments we will make in this step
        assignments = {}

        # Sort fields by threat level (descending)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        if not fields_sorted:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper: squared distance from drone to field center
        def dist2_to_center(drone, center):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return dx*dx + dy*dy

        # Function to estimate time to a target center (speed = 2)
        def time_to(center, drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dist = math.hypot(loc.x - center[0], loc.y - center[1])
            return dist / 2.0

        # Step: aggressively protect the top field using suitable candidates
        top_field = fields_sorted[0]
        top_id = top_field.id
        center_top = field_centers[top_id]
        current_top = protecting_counts.get(top_id, 0)
        needed_top = getattr(top_field, "drones_for_full_protection", 0) - current_top

        if needed_top > 0:
            pool = []
            for d in components:
                if d in assignments:
                    continue
                st = getattr(d, "state", None)
                fid = getattr(d, "target_id", None)

                # If already heading to the top field, it is effectively counted already
                if st == "moving_to_field" and fid == top_id:
                    continue

                if st == "idle":
                    pool.append(d)
                    continue

                if st == "moving_to_field" and fid is not None:
                    # Consider switching if time_to_top <= time_to_current_target
                    t_top = time_to(center_top, d)
                    if fid in field_centers:
                        center_cur = field_centers[fid]
                        t_cur = time_to(center_cur, d)
                    else:
                        t_cur = float('inf')

                    if t_top <= t_cur:
                        pool.append(d)
                # Do not pull drones currently protecting other fields unless they meet the above condition
            # Sort pool by closeness to the top field
            pool.sort(key=lambda dr: dist2_to_center(dr, center_top))
            to_take = min(needed_top, len(pool))
            for i in range(to_take):
                drone = pool[i]
                environment.assign_group(drone, f"protecting {top_id}")
                assignments[drone] = f"protecting {top_id}"
                protecting_counts[top_id] = protecting_counts.get(top_id, 0) + 1

        # After top field, allocate remaining idle drones to next fields in threat order
        idle_drones = [d for d in components if d not in assignments and getattr(d, "state", None) == "idle"]
        for field in fields_sorted[1:]:
            fid = field.id
            center = field_centers[fid]
            current = protecting_counts.get(fid, 0)
            needed = getattr(field, "drones_for_full_protection", 0) - current
            if needed <= 0:
                continue

            pool = list(idle_drones)
            pool.sort(key=lambda dr: dist2_to_center(dr, center))
            to_take = min(needed, len(pool))
            for i in range(to_take):
                drone = pool[i]
                environment.assign_group(drone, f"protecting {fid}")
                assignments[drone] = f"protecting {fid}"
                idle_drones.remove(drone)
                protecting_counts[fid] = protecting_counts.get(fid, 0) + 1

        # Final pass: explicit reassignment for all drones
        for d in components:
            if d in assignments:
                environment.assign_group(d, assignments[d])
            else:
                fid = getattr(d, "target_id", None)
                st = getattr(d, "state", None)
                if st in ("protecting", "moving_to_field") and fid is not None:
                    environment.assign_group(d, f"protecting {fid}")
                else:
                    environment.assign_group(d, "idle")