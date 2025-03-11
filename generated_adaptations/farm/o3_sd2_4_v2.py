import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare data structures.
        available_drones = []
        # Dictionary to keep track of additional assignments we make for each field.
        assigned_counts = {}
        # Build a dictionary to quickly lookup fields by id.
        field_by_id = {field.id: field for field in environment.fields if field.threat_level > 0}

        # Initialize assigned counts for each threatened field.
        for field in field_by_id.values():
            assigned_counts[field.id] = 0

        # Process each drone:
        # If a drone is already protecting a field with threat, we keep that assignment.
        # Otherwise, it becomes available for reassignment.
        for drone in components:
            # If the drone is protecting and its target corresponds to an active field, keep the assignment.
            if drone.state == "protecting" and drone.target_id in field_by_id:
                # Reassign to ensure it remains in the correct group.
                environment.assign_group(drone, f"protecting {drone.target_id}")
                assigned_counts[drone.target_id] += 1
            else:
                available_drones.append(drone)

        # Build a list of fields that need protection, calculating the missing drones required.
        fields_to_protect = []
        for field in field_by_id.values():
            # current drones protecting this field are those already assigned plus the ones arriving.
            current = field.protecting_drones + field.arriving_drones + assigned_counts[field.id]
            missing = max(0, field.necessary_drones_for_full_protection - current)
            # Only consider fields that still require additional drones.
            if missing > 0:
                fields_to_protect.append((field, missing))

        # Stage 1: Greedily assign available drones to fully protect fields where possible.
        # Sort fields by the number of extra drones needed (lowest first).
        fields_to_protect.sort(key=lambda tup: tup[1])
        for field, missing in fields_to_protect:
            if missing <= 0:
                continue
            # Only assign if we have enough available drones to reach full protection.
            if len(available_drones) >= missing:
                for _ in range(missing):
                    drone = available_drones.pop(0)
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_counts[field.id] += 1

        # Stage 2: Distribute any remaining available drones in a round-robin manner to fields that are still underprotected.
        # Recompute missing counts.
        fields_remaining = []
        for field, _ in fields_to_protect:
            current = field.protecting_drones + field.arriving_drones + assigned_counts[field.id]
            missing = max(0, field.necessary_drones_for_full_protection - current)
            if missing > 0:
                fields_remaining.append((field, missing))

        # Favor fields with higher threat levels.
        fields_remaining.sort(key=lambda tup: tup[0].threat_level, reverse=True)
        idx = 0
        while available_drones and fields_remaining:
            field, missing = fields_remaining[idx]
            drone = available_drones.pop(0)
            environment.assign_group(drone, f"protecting {field.id}")
            assigned_counts[field.id] += 1
            missing -= 1
            fields_remaining[idx] = (field, missing)
            # Remove field if it has reached full protection.
            if missing <= 0:
                fields_remaining.pop(idx)
                if not fields_remaining:
                    break
                idx = idx % len(fields_remaining)
            else:
                idx = (idx + 1) % len(fields_remaining)

        # Stage 3: Assign any remaining available drones to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
