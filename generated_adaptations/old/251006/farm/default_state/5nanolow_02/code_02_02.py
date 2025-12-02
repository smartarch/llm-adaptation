import abc

# The base class is expected to be importable from the given path
from generated_adaptations.base_classes.farm import FarmAdaptation as _BaseFarmAdaptation

class SmartFarmAdaptation(_BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        More robust adaptation strategy:
        - Consider fields with positive threat_level, sorted by threat (high -> low).
        - For each field in that order, ensure full protection by allocating drones.
        - Drones currently protecting the field are preserved (count towards protection).
        - Drones not yet protecting that field are assigned to it until full protection is reached.
        - All other drones default to idle.
        - This aims to maximize protection coverage for the most threatening fields while minimizing movement.
        """
        # Gather fields and helpers
        fields = list(environment.fields)

        # Current protection counts per field (based on observed drones)
        current_protecting = {field.id: 0 for field in fields}
        for drone in components:
            if drone.state == "protecting" and drone.target_id is not None:
                tid = drone.target_id
                current_protecting[tid] = current_protecting.get(tid, 0) + 1

        # List of fields that deserve attention, sorted by threat_level desc
        candidates = [f for f in fields if getattr(f, "threat_level", 0) > 0]
        candidates.sort(key=lambda f: f.threat_level, reverse=True)

        # Prepare assignment: start by making everyone idle
        for drone in components:
            environment.assign_group(drone, "idle")

        if not candidates:
            return  # nothing to defend

        # For each candidate field, ensure full protection
        assigned_ids = set()  # tracks drones we have explicitly assigned in this call

        for field in candidates:
            field_id = field.id
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - current_protecting.get(field_id, 0))
            if needed == 0:
                # Field already fully protected; skip to next
                # but mark any currently protecting this field as assigned to that field
                for drone in components:
                    if drone.state == "protecting" and drone.target_id == field_id:
                        environment.assign_group(drone, f"protecting {field_id}")
                        assigned_ids.add(id(drone))
                continue

            # First, ensure drones already protecting this field stay assigned
            for drone in components:
                if drone.state == "protecting" and drone.target_id == field_id:
                    environment.assign_group(drone, f"protecting {field_id}")
                    assigned_ids.add(id(drone))

            # Then allocate additional drones from the pool to this field
            if needed > 0:
                for drone in components:
                    if needed == 0:
                        break
                    if id(drone) in assigned_ids:
                        continue
                    # Assign this drone to protect this field
                    environment.assign_group(drone, f"protecting {field_id}")
                    assigned_ids.add(id(drone))
                    needed -= 1

        # Any drones not assigned yet remain idle (already set to idle at start)