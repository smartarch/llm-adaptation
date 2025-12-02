from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute distance from drone to a point
        def dist_point_to_drone(drone_location, x, y):
            dx = drone_location.x - x
            dy = drone_location.y - y
            return (dx * dx + dy * dy) ** 0.5

        # Gather fields with threat > 0
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Map field_id -> list of drones currently protecting that field
        protecting_map = {f.id: [] for f in fields_with_threat}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in protecting_map:
                    protecting_map[tid].append(d)

        # Determine highest-threat field
        highest_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))
        highest_id = highest_field.id
        hx, hy = field_center(highest_field)

        # Drones needed for highest field
        needed_for_highest = int(getattr(highest_field, "drones_for_full_protection", 0)) - len(protecting_map.get(highest_id, []))
        if needed_for_highest < 0:
            needed_for_highest = 0

        # Track which drones we've assigned in this step
        assigned = set()

        # Drones not currently protecting the highest field
        candidates_for_highest = [
            d for d in components
            if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == highest_id)
        ]
        candidates_for_highest.sort(key=lambda d: dist_point_to_drone(d.location, hx, hy))

        # Assign closest drones to highest field until fully protected or we run out
        for i in range(min(needed_for_highest, len(candidates_for_highest))):
            d = candidates_for_highest[i]
            env_group = f"protecting {highest_id}"
            environment.assign_group(d, env_group)
            assigned.add(d)
        
        # After attempting highest field, try to protect other fields by threat order
        other_fields = [f for f in fields_with_threat if f.id != highest_id]
        other_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for f in other_fields:
            fid = f.id
            fx, fy = field_center(f)
            current = len(protecting_map.get(fid, []))
            need = int(getattr(f, "drones_for_full_protection", 0)) - current
            if need <= 0:
                continue

            # Build candidate pool: not already assigned in this step and not already protecting this field
            pool = [
                d for d in components
                if d not in assigned and not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid)
            ]

            pool.sort(key=lambda d: dist_point_to_drone(d.location, fx, fy))
            take = min(need, len(pool))
            for i in range(take):
                d = pool[i]
                environment.assign_group(d, f"protecting {fid}")
                assigned.add(d)

        # Any remaining drones become idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")