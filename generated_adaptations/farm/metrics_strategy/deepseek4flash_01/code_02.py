from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat level
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        
        if not active_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return
        
        # Sort by threat level descending, then by id for determinism
        active_fields.sort(key=lambda f: (-f.threat_level, f.id))
        
        # Precompute field centers
        field_centers = {}
        for f in active_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)
        
        # Categorize drones based on their current target/state
        current_field_drones = {f.id: [] for f in active_fields}
        idle_drones = []
        for drone in components:
            if drone.target_id in current_field_drones and drone.state in ("moving_to_field", "protecting"):
                current_field_drones[drone.target_id].append(drone)
            else:
                idle_drones.append(drone)
        
        unassigned = set(components)
        idle_set = set(idle_drones)
        
        # Process fields in order of priority
        for field in active_fields:
            required = field.drones_for_full_protection
            if required <= 0:
                continue
            
            field_id = field.id
            center = field_centers[field_id]
            
            # Keep existing drones on this field up to the required amount
            assigned = []
            for drone in current_field_drones[field_id]:
                if drone in unassigned and len(assigned) < required:
                    assigned.append(drone)
                    unassigned.remove(drone)
            
            # Fill the remaining need with closest unassigned drones
            needed = required - len(assigned)
            if needed > 0:
                candidates = list(unassigned)
                def sort_key(d):
                    dx = d.location.x - center[0]
                    dy = d.location.y - center[1]
                    dist_sq = dx*dx + dy*dy
                    # Prefer idle drones only when distances are equal
                    return (dist_sq, 0 if d in idle_set else 1)
                candidates.sort(key=sort_key)
                for drone in candidates[:needed]:
                    assigned.append(drone)
                    unassigned.remove(drone)
            
            # Assign the chosen drones to this field's group
            group_name = f"protecting {field_id}"
            for drone in assigned:
                environment.assign_group(drone, group_name)
            
            # If no unassigned drones left, stop early
            if not unassigned:
                break
        
        # Remaining drones stay idle
        for drone in unassigned:
            environment.assign_group(drone, "idle")