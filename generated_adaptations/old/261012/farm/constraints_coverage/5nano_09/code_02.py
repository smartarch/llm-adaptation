from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Determine the field with the highest threat (> 0)
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            if getattr(f, "threat_level", 0) > 0:
                if f.threat_level > max_threat:
                    max_threat = f.threat_level
                    top_field = f

        # If no threatening field, idle all drones (if possible)
        if top_field is None:
            for drone in components:
                if "idle" in group_ids:
                    environment.assign_group(drone, "idle")
                else:
                    # Fallback: assign to any available group (best-effort)
                    if group_ids:
                        environment.assign_group(drone, group_ids[0])
            return

        # Compute the center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # How many drones are needed for full protection
        required = getattr(top_field, "drones_for_full_protection", 0)
        if required <= 0:
            # If somehow the field requires 0 drones, just idle all (or keep existing protection if any)
            for drone in components:
                if "idle" in group_ids:
                    environment.assign_group(drone, "idle")
                else:
                    if group_ids:
                        environment.assign_group(drone, group_ids[0])
            return

        # Compute distances to the field center for all drones
        dist_list = []
        for drone in components:
            dx = getattr(drone, "location").x - cx
            dy = getattr(drone, "location").y - cy
            dist = math.hypot(dx, dy)
            dist_list.append((dist, drone))

        # Sort drones by distance (closest first)
        dist_list.sort(key=lambda t: t[0])

        # Determine which drones should protect the top field
        num_drones = min(required, len(components))
        protect_group = f"protecting {top_field.id}"
        assign_to_protect = []
        assign_to_idle = []

        # If the protect group name is not valid, fall back to idle
        valid_protect_group = protect_group in group_ids

        for i, (dist, drone) in enumerate(dist_list):
            if i < num_drones and valid_protect_group:
                assign_to_protect.append(drone)
            else:
                assign_to_idle.append(drone)

        # Assign groups explicitly
        if valid_protect_group:
            for d in assign_to_protect:
                environment.assign_group(d, protect_group)

        # Idle for the rest
        for d in assign_to_idle:
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            else:
                # Fallback to first available group
                if group_ids:
                    environment.assign_group(d, group_ids[0])