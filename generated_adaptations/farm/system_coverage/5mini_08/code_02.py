from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into groups:
        - "idle" for idle drones / those not protecting the top-threat field
        - "protecting {field.id}" for drones assigned to fully protect the highest-threat field

        Strategy:
        1. Find all fields with threat_level > 0. If none, assign all drones to "idle".
        2. Select the field with the highest threat_level (tie-break by field.id).
        3. Count committed drones (any drone whose target_id == field.id).
        4. If committed < drones_for_full_protection, pick the closest other drones to the field center
           to reach the required number.
        5. Assign all drones whose target_id == field.id and the selected closest drones to
           "protecting {field.id}". Assign every other drone to "idle".
        """
        # Helper to compute distance from drone to field center
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy)

        # Build list of candidate fields (threat_level > 0)
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no field needs protection, assign all drones to idle
        if not candidate_fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # fallback: if "idle" not present (should not happen), pick first group
                    environment.assign_group(comp, group_ids[0])
            return

        # Select field with highest threat_level; tie-break by field.id lexicographically
        candidate_fields.sort(key=lambda f: (f.threat_level, f.id), reverse=True)
        target_field = candidate_fields[0]
        protect_group = f"protecting {target_field.id}"
        # If the required group is not present in group_ids, fall back to "idle" for safety
        if protect_group not in group_ids:
            # If protecting group isn't valid, assign everyone idle (defensive)
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    environment.assign_group(comp, group_ids[0])
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Drones already committed to this field (target_id == field.id)
        committed = [c for c in components if c.target_id == target_field.id]

        # If already enough committed drones, keep them; else pick additional closest drones
        assigned_protecting = set()
        for c in committed:
            assigned_protecting.add(c)

        if len(committed) < required:
            # Consider all drones not already committed
            others = [c for c in components if c.target_id != target_field.id]
            # Sort others by distance to field center
            others.sort(key=lambda c: distance_to_field_center(c, target_field))
            needed = required - len(committed)
            for c in others[:needed]:
                assigned_protecting.add(c)

        # Now assign groups: protecting group for assigned_protecting, idle for others
        for c in components:
            if c in assigned_protecting:
                environment.assign_group(c, protect_group)
            else:
                # assign to idle (must be present in group_ids)
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
                else:
                    environment.assign_group(c, group_ids[0])