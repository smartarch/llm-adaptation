from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        threatened_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0
        ]
        
        # Helper to assign a drone to a group if it's valid, else to idle
        def assign_group_safe(drone, group_name):
            if group_name in group_ids:
                environment.assign_group(drone, group_name)
            else:
                environment.assign_group(drone, "idle")
        
        # If no threatened fields, keep everyone idle
        if not threatened_fields:
            for d in components:
                assign_group_safe(d, "idle")
            return
        
        # Preserve drones already protecting a field (explicit re-assign to same group)
        threat_field_ids = {f.id for f in threatened_fields}
        assigned = set()  # track drones we explicitly assigned to a protecting group
        
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in threat_field_ids:
                grp = f"protecting {d.target_id}"
                assign_group_safe(d, grp)
                assigned.add(id(d))
        
        # Sort fields by threat level (desc). If needed, use drones_for_full_protection as tie-breaker
        fields_sorted = sorted(
            threatened_fields,
            key=lambda f: (getattr(f, "threat_level", 0),
                           getattr(f, "drones_for_full_protection", 0)),
            reverse=True
        )
        
        # Allocate drones to fields in order of priority
        for f in fields_sorted:
            field_id = f.id
            center_x = (f.left + f.right) / 2.0
            center_y = (f.top + f.bottom) / 2.0
            full_needed = int(getattr(f, "drones_for_full_protection", 0))
            
            # Count drones currently protecting this field
            current_protecting = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id
            ]
            current_count = len(current_protecting)
            needed = max(0, full_needed - current_count)
            if needed <= 0:
                # Field already fully protected; keep current drones assigned
                continue
            
            # Build candidate pool: drones not currently protecting this field
            candidates = []
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    continue
                dist = ((loc.x - center_x) ** 2 + (loc.y - center_y) ** 2) ** 0.5
                candidates.append((dist, d))
            
            candidates.sort(key=lambda t: t[0])
            
            # Assign the closest drones to protect this field
            protect_group = f"protecting {field_id}"
            assigned_count = 0
            for _, d in candidates:
                if assigned_count >= needed:
                    break
                assign_group_safe(d, protect_group)
                assigned.add(id(d))
                assigned_count += 1
        
        # Finally, assign all drones not yet assigned to a protecting group or idle
        for d in components:
            if id(d) in assigned:
                # Already assigned to a protecting group
                continue
            # If drone is currently protecting a field that still has threat, it would have been assigned above.
            # Otherwise, move to idle
            assign_group_safe(d, "idle")