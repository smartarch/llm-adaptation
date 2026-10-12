from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        fields_with_threat = [
            f for f in environment.fields if getattr(f, "threat_level", 0) > 0
        ]

        # If no threats, idle all drones
        if not fields_with_threat:
            for c in components:
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else None)
                if grp:
                    environment.assign_group(c, grp)
            return

        # Sort fields by threat level descending
        fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

        # Helper to compute field center
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper to compute squared distance from drone to a field center
        def dist_sq(drone, cx, cy):
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return dx*dx + dy*dy

        # Prepare pool of drones to allocate
        pool = list(components)

        # Helper to map a field to a valid group name
        def group_for_field(field_id):
            grp = f"protecting {field_id}"
            if grp in group_ids:
                return grp
            # Fallback to idle if the protecting group isn't valid
            return "idle" if "idle" in group_ids else None

        # Clear any previous explicit allocations by assigning all to new plan
        # We'll build assignments per drone by taking from the pool.
        for field in fields_sorted:
            if not pool:
                break

            center_x, center_y = center(field)

            # How many drones we should try to allocate to this field fully
            desired_full = max(0, getattr(field, "drones_for_full_protection", 0))

            if desired_full > 0 and len(pool) >= desired_full:
                # Choose the closest 'desired_full' drones to this field
                pool.sort(key=lambda d: dist_sq(d, center_x, center_y))
                chosen = pool[:desired_full]
                pool = pool[desired_full:]

                grp = group_for_field(field.id)
                if grp:
                    for d in chosen:
                        environment.assign_group(d, grp)
                # Continue to next field with remaining drones
            else:
                # Not enough drones to fully protect this field (or desired_full == 0)
                # Allocate all remaining drones to this field for partial protection
                if pool:
                    pool.sort(key=lambda d: dist_sq(d, center_x, center_y))
                    chosen = list(pool)
                    pool = []

                    grp = group_for_field(field.id)
                    if grp:
                        for d in chosen:
                            environment.assign_group(d, grp)
                break

        # Any remaining drones, assign to idle (if available)
        if pool:
            idle_grp = "idle" if "idle" in group_ids else None
            if idle_grp:
                for d in pool:
                    environment.assign_group(d, idle_grp)
            # If no idle group is available, we simply leave them unchanged (no further assignment)