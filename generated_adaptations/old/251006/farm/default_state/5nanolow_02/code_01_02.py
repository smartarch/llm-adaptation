import abc

# The base class is expected to be importable from the given path
from generated_adaptations.base_classes.farm import FarmAdaptation as _BaseFarmAdaptation

class SmartFarmAdaptation(_BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into groups:
        - "idle": idle drones
        - "protecting {field_id}": drones protecting a specific field
        Strategy: Fully protect the field with the highest threat level that is not yet fully protected.
        """
        # Build a mapping for faster lookups
        # Also collect fields with threat_level > 0
        fields = list(environment.fields)

        # Determine current protection per field: count drones currently protecting that field
        current_protecting = {}
        for field in fields:
            current_protecting[field.id] = 0

        for drone in components:
            if drone.state == "protecting" and drone.target_id is not None:
                tid = drone.target_id
                current_protecting[tid] = current_protecting.get(tid, 0) + 1

        # Determine the best field to protect: highest threat_level > 0
        best_field = None
        best_threat = -1.0
        for field in fields:
            if field.threat_level > 0:
                if field.threat_level > best_threat:
                    best_threat = field.threat_level
                    best_field = field

        # Default: assign all drones to idle
        for drone in components:
            environment.assign_group(drone, "idle")

        if best_field is None:
            # No field requires attention right now
            return

        # How many drones are needed to fully protect this field?
        needed_total = getattr(best_field, "drones_for_full_protection", 0)
        current = current_protecting.get(best_field.id, 0)
        need = max(0, needed_total - current)

        if need <= 0:
            # Already fully protected; keep current protection as is
            return

        # Assign drones to protect the best field until it's full
        # Do not move drones that are already protecting this field
        assigned = 0
        for drone in components:
            if assigned >= need:
                break
            if drone.state == "protecting" and drone.target_id == best_field.id:
                # Already protecting this field; skip
                continue
            # If we still need drones, assign this drone to the best field
            environment.assign_group(drone, f"protecting {best_field.id}")
            assigned += 1

        # Any remaining drones (not yet assigned to the best field) will stay idle (already set above)