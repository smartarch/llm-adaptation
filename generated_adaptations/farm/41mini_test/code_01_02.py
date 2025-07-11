from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Sort fields by descending threat level, ignoring fields with zero threat
        threat_fields = [field for field in environment.fields if field.threat_level > 0]
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        
        # Calculate how many drones each field still needs for full protection
        drones_needed_for_field = {}
        for field in threat_fields:
            needed = field.drones_for_full_protection - (field.protecting_drones + field.arriving_drones)
            drones_needed_for_field[field.id] = max(0, needed)
        
        # Group names for fields with threat
        protecting_groups = {field.id: f"protecting {field.id}" for field in threat_fields}
        
        # Track assignments: drone id -> group id (field protection or idle)
        assignments = {}
        
        # List of drones that are not yet assigned
        unassigned_drones = list(components)
        
        # Assign drones that are already assigned to a protecting group for fields with threat if still needed
        # We keep these assignments unless more are needed for the field.
        # This avoids unnecessary drone movement.
        for drone in components:
            if drone.state == "protecting" or drone.state == "moving_to_field":
                target = drone.target_id
                group_name = f"protecting {target}" if target in drones_needed_for_field else None
                # Only assign if field still needs drones or drone is protecting/moving to that field
                if group_name is not None:
                    if drones_needed_for_field[target] > 0:
                        assignments[drone] = group_name
                        drones_needed_for_field[target] -= 1
                        unassigned_drones.remove(drone)
        
        # Assign remaining drones to fields needing drones by priority
        for field in threat_fields:
            group_name = f"protecting {field.id}"
            needed = drones_needed_for_field[field.id]
            if needed > 0:
                for drone in list(unassigned_drones):
                    assignments[drone] = group_name
                    unassigned_drones.remove(drone)
                    needed -= 1
                    if needed == 0:
                        break
                drones_needed_for_field[field.id] = needed
        
        # Assign remaining drones to idle
        for drone in unassigned_drones:
            assignments[drone] = "idle"
        
        # Assign drones to their groups using environment.assign_group
        for drone, group in assignments.items():
            environment.assign_group(drone, group)