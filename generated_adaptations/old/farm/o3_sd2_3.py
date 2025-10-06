from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Build a mapping from field id to its required number of drones
        field_demands = {}
        # Only consider fields with threat_level > 0 and valid group id.
        for field in environment.fields:
            group_name = f"protecting {field.id}"
            if field.threat_level > 0 and group_name in group_ids:
                # Calculate additional drones needed for full protection.
                # It is possible that some drones are already arriving or protecting.
                needed = field.drones_for_full_protection - field.protecting_drones - field.arriving_drones
                field_demands[field.id] = max(0, needed)

        # Sort the fields in descending order by threat level (fields with higher threat get priority)
        fields_sorted = sorted(
            [field for field in environment.fields if field.threat_level > 0 and f"protecting {field.id}" in group_ids],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # Make a copy of the remaining demand per field
        remaining_demand = {field.id: field_demands.get(field.id, 0) for field in fields_sorted}

        # Iterate over each drone and assign it to the field with remaining demand if possible.
        for drone in components:
            assigned = False
            # Try to assign the drone to a field that still requires more drones.
            for field in fields_sorted:
                if remaining_demand[field.id] > 0:
                    environment.assign_group(drone, f"protecting {field.id}")
                    remaining_demand[field.id] -= 1
                    assigned = True
                    break  # Stop looking after assigning to one field.
            # If no field needs additional drones, set the drone as idle.
            if not assigned:
                environment.assign_group(drone, "idle")
