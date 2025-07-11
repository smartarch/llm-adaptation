from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Filter fields with threat and calculate drones needed for full protection
        threat_fields = [field for field in environment.fields if field.threat_level > 0]
        if not threat_fields:
            # No threat, assign all drones idle
            for drone in components:
                environment.assign_group(drone, "idle")
            return
        
        # Calculate drones needed for each field
        drones_needed = {}
        for field in threat_fields:
            needed = field.drones_for_full_protection - (field.protecting_drones + field.arriving_drones)
            drones_needed[field.id] = max(0, needed)
        
        # Map field id to group name
        field_groups = {field.id: f"protecting {field.id}" for field in threat_fields}
        
        # Assign drones already protecting or moving to a still-needed field first
        assignments = {}
        unassigned_drones = set(components)
        
        for drone in components:
            if drone.state in ("protecting", "moving_to_field") and drone.target_id in drones_needed:
                target = drone.target_id
                if drones_needed[target] > 0:
                    assignments[drone] = field_groups[target]
                    drones_needed[target] -= 1
                    unassigned_drones.discard(drone)
        
        # Precompute some helper: function to get drone-to-field Euclidean distance
        def dist(drone_loc, field):
            # Use center of the field as point approximation
            fx = (field.left + field.right) / 2
            fy = (field.top + field.bottom) / 2
            dx = drone_loc.x - fx
            dy = drone_loc.y - fy
            return math.sqrt(dx*dx + dy*dy)
        
        # List of fields with drones needed > 0
        needy_fields = [field for field in threat_fields if drones_needed[field.id] > 0]
        
        # For every unassigned drone, assign it to the best field considering threat and closeness
        # Score = threat_level / (distance + 1) to prioritize closer high threat fields
        for drone in list(unassigned_drones):
            best_score = 0
            best_field_id = None
            for field in needy_fields:
                if drones_needed[field.id] <= 0:
                    continue
                distance = dist(drone.location, field)
                score = field.threat_level / (distance + 1e-6 + 1)  # add 1 to avoid div by zero and 1e-6 for safety
                if score > best_score:
                    best_score = score
                    best_field_id = field.id
            
            if best_field_id is not None:
                assignments[drone] = field_groups[best_field_id]
                drones_needed[best_field_id] -= 1
                unassigned_drones.discard(drone)
                # Update needy_fields list if field is fully assigned
                if drones_needed[best_field_id] <= 0:
                    needy_fields = [field for field in needy_fields if field.id != best_field_id]
            else:
                # No beneficial assignment, assign idle
                assignments[drone] = "idle"
                unassigned_drones.discard(drone)
        
        # In case any drones are still unassigned, assign idle explicitly
        for drone in unassigned_drones:
            assignments[drone] = "idle"
        
        # Finally assign groups
        for drone, group in assignments.items():
            environment.assign_group(drone, group)