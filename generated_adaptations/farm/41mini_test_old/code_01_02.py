from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Fields with threat_level > 0, sorted descending by threat_level
        threat_fields = [field for field in environment.fields if field.threat_level > 0]
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Calculate how many drones are needed for full protection per field
        field_needs = {}
        for field in threat_fields:
            assigned_drones = field.arriving_drones + field.protecting_drones
            needed = max(0, field.drones_for_full_protection - assigned_drones)
            field_needs[field.id] = needed

        # We will assign drones stepwise to these fields to cover needed drones
        # Start drones assignments: keep track of how many assigned to each field here
        assigned_count = {field.id: 0 for field in threat_fields}

        # To avoid unnecessary switches: prefer to keep drones assigned to the field they are moving to or protecting
        # Build sets for quick lookup
        threatened_field_ids = set(field.id for field in threat_fields)

        # Assign drones first those already assigned to threatened fields if still needed
        free_drones = []
        for drone in components:
            current_target = drone.target_id
            # If drone targeting a threatened field and field still needs drones
            if current_target in threatened_field_ids and field_needs[current_target] > 0:
                # Assign drone to that field
                environment.assign_group(drone, f"protecting {current_target}")
                assigned_count[current_target] += 1
                field_needs[current_target] -= 1
            else:
                # Drone not currently targeting a threatened field or no more needed, keep for future assignment
                free_drones.append(drone)

        # Assign remaining drones (free_drones) to fields with remaining needs, in order of threat level
        for drone in free_drones:
            assigned = False
            for field in threat_fields:
                if field_needs[field.id] > 0:
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_count[field.id] += 1
                    field_needs[field.id] -= 1
                    assigned = True
                    break
            if not assigned:
                # No fields need more drones or no threat fields - assign drone to idle
                environment.assign_group(drone, "idle")