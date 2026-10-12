from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]
        
        # Helper to safely assign a drone to a group (only if the group exists)
        def assign_group_safe(drone, group_name):
            if group_name in group_ids:
                environment.assign_group(drone, group_name)
            else:
                environment.assign_group(drone, "idle")
        
        # If no threats, send everyone idle
        if not fields_with_threat:
            for drone in components:
                assign_group_safe(drone, "idle")
            return
        
        # Choose the field with the highest threat (tie-breaker by drones_for_full_protection if available)
        field_to_protect = max(
            fields_with_threat,
            key=lambda f: (
                getattr(f, "threat_level", 0),
                getattr(f, "drones_for_full_protection", 0)
            )
        )
        field_id = field_to_protect.id
        # Field center (approximate as center of bounding box)
        cx = (field_to_protect.left + field_to_protect.right) / 2.0
        cy = (field_to_protect.top + field_to_protect.bottom) / 2.0

        # Count drones already protecting this field
        currently_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id
        ]
        current_protecting_count = len(currently_protecting)

        # Required drones for full protection on this field
        required_for_full = getattr(field_to_protect, "drones_for_full_protection", 0)
        needed = max(0, int(required_for_full) - current_protecting_count)

        # Build candidate drones (not currently protecting this field)
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                # Already protecting this field; skip for reallocation (can keep last phase)
                continue
            loc = getattr(d, "location", None)
            if loc is None:
                continue
            dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
            candidates.append((dist, d))

        # Sort by distance (closest first)
        candidates.sort(key=lambda t: t[0])

        # Assign the closest drones to protect this field, up to the needed amount
        assigned = 0
        protect_group = f"protecting {field_id}"
        for _, drone in candidates:
            if assigned >= needed:
                break
            assign_group_safe(drone, protect_group)
            assigned += 1

        # Finally, assign all other drones to idle (preserving current protection on the top field if already fully protected)
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                # Keep drones already protecting this field in its protect group (explicitly re-assign to keep state consistent)
                assign_group_safe(d, protect_group)
            else:
                assign_group_safe(d, "idle")