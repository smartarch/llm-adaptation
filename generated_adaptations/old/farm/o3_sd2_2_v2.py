from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Create a lookup of fields with a threat level > 0
        threatened_fields = {field.id: field for field in environment.fields if field.threat_level > 0}

        # This dictionary will track drones already assigned (or being re-assigned) to protecting groups
        assigned_protectors = {field_id: [] for field_id in threatened_fields}

        # List for drones that are available for new assignments
        available_drones = []

        # First pass: for each drone, if it is already targeting a threatened field and is in a protecting or moving state,
        # reassign it to the corresponding protecting group.
        for drone in components:
            if drone.target_id in threatened_fields and drone.state in ["protecting", "moving_to_field"]:
                environment.assign_group(drone, f"protecting {drone.target_id}")
                assigned_protectors[drone.target_id].append(drone)
            else:
                available_drones.append(drone)

        # Sort the available drones giving preference to idle ones.
        available_drones = sorted(available_drones, key=lambda d: 0 if d.state == "idle" else 1)

        # For each threatened field, assign additional drones if needed.
        for field_id, field in threatened_fields.items():
            # Already en route or protecting drones (assigned in our pass above) plus those reported as arriving
            current_assigned = len(assigned_protectors[field_id])
            # Calculate drones missing to reach full protection (considering arriving drones reported by sensors)
            drones_needed = max(0, field.drones_for_full_protection - (field.arriving_drones + current_assigned))

            for _ in range(drones_needed):
                if available_drones:
                    drone = available_drones.pop(0)
                    environment.assign_group(drone, f"protecting {field_id}")
                    assigned_protectors[field_id].append(drone)

        # Any remaining drones should be assigned to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
