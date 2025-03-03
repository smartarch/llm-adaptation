import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Make a local copy of all available drones.
        available_drones = list(components)

        # We keep track of the number of drones we assign to each field
        assigned_counts = {}  # field.id -> number assigned by our strategy
        fields_to_protect = []
        for field in environment.fields:
            # Consider only fields with some bird threat.
            if field.threat_level > 0:
                assigned_counts[field.id] = 0
                # Calculate how many additional drones are needed for full protection.
                current = field.protecting_drones + field.arriving_drones
                missing = max(0, field.necessary_drones_for_full_protection - current)
                # Store the field along with the missing number
                fields_to_protect.append((field, missing))

        # Stage 1: Greedily assign drones to fully protect fields that need few extra drones.
        # Sort fields by how many extra drones they need (lowest first)
        fields_to_protect.sort(key=lambda tup: tup[1])

        # Try to fully protect fields when we can
        for field, missing in fields_to_protect:
            # Skip if no additional drones are needed (already fully protected)
            if missing <= 0:
                continue
            # Only assign if we have enough drones available to reach full protection.
            if len(available_drones) >= missing:
                for _ in range(missing):
                    drone = available_drones.pop(0)
                    environment.assign_group(drone, f"protecting {field.id}")
                    assigned_counts[field.id] += 1
            # If not enough drones remain to fully protect this field, we leave it for stage 2.

        # Stage 2: With any remaining drones, distribute them to fields that are still underprotected.
        # Build a list of fields (with current missing updated) that are not yet fully protected.
        fields_remaining = []
        for field, _ in fields_to_protect:
            current = field.protecting_drones + field.arriving_drones + assigned_counts[field.id]
            missing = max(0, field.necessary_drones_for_full_protection - current)
            if missing > 0:
                fields_remaining.append((field, missing))

        # If there are fields still needing extra drones, distribute available drones round-robin.
        # Here we sort by threat level descending so that fields with higher bird pressure are favored.
        fields_remaining.sort(key=lambda tup: tup[0].threat_level, reverse=True)
        idx = 0
        while available_drones and fields_remaining:
            field, missing = fields_remaining[idx]
            drone = available_drones.pop(0)
            environment.assign_group(drone, f"protecting {field.id}")
            assigned_counts[field.id] += 1
            missing -= 1
            # Update the missing count for this field.
            fields_remaining[idx] = (field, missing)
            # If the field is now fully protected, remove it from our list.
            if missing <= 0:
                fields_remaining.pop(idx)
                # If list becomes empty, break out.
                if not fields_remaining:
                    break
                # Otherwise, reset idx if needed.
                idx = idx % len(fields_remaining)
            else:
                # Move to the next field in round-robin order.
                idx = (idx + 1) % len(fields_remaining)

        # Stage 3: Any drones that remain are not needed for protection so they are assigned to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
