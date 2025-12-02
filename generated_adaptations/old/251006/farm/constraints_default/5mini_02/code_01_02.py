from math import sqrt, ceil
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the single field with the highest threat_level is fully protected
        by the closest drones. Keep drones already protecting that field in place. Remaining
        drones are assigned to 'idle'.
        """
        # Helper to compute Euclidean distance between drone and field center
        def distance_to_field(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return sqrt(dx * dx + dy * dy)

        # Ensure "idle" group exists (fallback) and gather protect group names
        idle_group = "idle"
        if idle_group not in group_ids and len(group_ids) > 0:
            # fallback to first available group if "idle" missing (shouldn't happen)
            idle_group = group_ids[0]

        # Find fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threatened_fields:
            # No threats: assign all drones to idle
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Select the highest-threat field (deterministic tie-break by id)
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        target_field = threatened_fields[0]

        # Compose protecting group name and verify it exists in group_ids; otherwise fallback to idle
        protecting_group_name = f"protecting {target_field.id}"
        if protecting_group_name not in group_ids:
            protecting_group_name = idle_group

        # Number of drones required for full protection (ensure integer)
        try:
            required = int(ceil(getattr(target_field, "drones_for_full_protection", 0)))
        except Exception:
            required = int(getattr(target_field, "drones_for_full_protection", 0))

        if required <= 0:
            # Nothing required: assign all drones to idle
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Identify drones already protecting the target field
        already_protecting = []
        others = []
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == target_field.id:
                already_protecting.append(c)
            else:
                others.append(c)

        # If already sufficient, keep them (do not strip extras)
        assigned_protectors = list(already_protecting)

        # If more needed, pick closest from others
        if len(assigned_protectors) < required:
            # Compute distances for remaining drones
            others_sorted = sorted(others, key=lambda d: distance_to_field(d, target_field))
            needed = required - len(assigned_protectors)
            to_add = others_sorted[:needed]
            assigned_protectors.extend(to_add)
            # Remove selected from others so they are not assigned idle later
            remaining_after_selection = [d for d in others if d not in to_add]
        else:
            remaining_after_selection = others  # none moved to protect group

        # Now assign groups: protecting drones to protecting_group_name, others to idle
        protect_set = set(assigned_protectors)
        for c in components:
            if c in protect_set:
                environment.assign_group(c, protecting_group_name)
            else:
                environment.assign_group(c, idle_group)