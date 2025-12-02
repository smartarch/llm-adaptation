from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat levels
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        idle_group = "idle"

        final_group_for = {}

        if not threat_fields:
            # No threats: all drones go idle (one assignment per drone)
            for d in components:
                final_group_for[d] = idle_group
        else:
            # Sort threat fields by threat level (highest first)
            threat_fields_sorted = sorted(threat_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
            top_field = threat_fields_sorted[0]
            top_group = f"protecting {top_field.id}"
            drones_for_full = int(getattr(top_field, "drones_for_full_protection", 0) or 0)

            # Current protectors on top field
            current_top = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id
            ]
            assigned = set(current_top)

            # Assign current top protectors to the top group
            for d in current_top:
                final_group_for[d] = top_group

            needed_top = max(0, drones_for_full - len(current_top))

            # Center of the top field for distance calculations
            cx_top = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy_top = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            # Gather candidates not yet assigned to top field
            candidates = []
            for d in components:
                if d in assigned:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dx = dy = 0.0
                else:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                dist2 = (dx - cx_top) ** 2 + (dy - cy_top) ** 2
                candidates.append((dist2, d))
            candidates.sort(key=lambda t: t[0])

            # Move the closest drones to top field until full protection reached
            for i in range(min(needed_top, len(candidates))):
                _, drone = candidates[i]
                final_group_for[drone] = top_group
                assigned.add(drone)

            # Distribute remaining drones to secondary threatened fields
            remaining_fields = threat_fields_sorted[1:]  # exclude top field
            remaining_drones = [d for d in components if d not in assigned]

            if remaining_drones and remaining_fields:
                # Simple proportional distribution: iterate secondary fields in order
                for f in remaining_fields:
                    field_group = f"protecting {f.id}"
                    # Current protectors on this field
                    current_on_field = [
                        d for d in components
                        if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == f.id
                    ]
                    # Ensure current protectors are assigned to the field group
                    for d in current_on_field:
                        if d not in final_group_for:
                            final_group_for[d] = field_group
                            assigned.add(d)

                    need_field = max(0, int(getattr(f, "drones_for_full_protection", 0) or 0) - len(current_on_field))
                    if need_field <= 0:
                        continue

                    # Center of this field
                    cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
                    cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0

                    pool = []
                    for d in remaining_drones:
                        if d in assigned:
                            continue
                        loc = getattr(d, "location", None)
                        if loc is None:
                            dx = dy = 0.0
                        else:
                            dx = getattr(loc, "x", 0.0)
                            dy = getattr(loc, "y", 0.0)
                        dist2 = (dx - cx) ** 2 + (dy - cy) ** 2
                        pool.append((dist2, d))
                    pool.sort(key=lambda t: t[0])

                    assign_count = min(need_field, len(pool))
                    for i in range(assign_count):
                        _, drone = pool[i]
                        final_group_for[drone] = field_group
                        assigned.add(drone)
                        remaining_drones.remove(drone)

            # Any drones not assigned to a protecting group become idle
            for d in components:
                if d not in final_group_for:
                    final_group_for[d] = idle_group

        # Apply final assignments exactly once per drone
        for d, g in final_group_for.items():
            environment.assign_group(d, g)