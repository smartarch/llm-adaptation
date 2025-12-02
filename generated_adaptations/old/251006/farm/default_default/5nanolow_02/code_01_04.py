import abc

# The following import path is assumed by the prompt environment.
# It provides the base class that our adaptation must extend.
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy:
    - Identify the field with the highest threat level (> 0).
    - Ensure that field has full protection by assigning drones to the group
      "protecting <field_id>" until the required number of drones (field.drones_for_full_protection)
      are present protecting it. If fewer drones are currently protecting it, allocate
      additional drones from the pool of idle drones to that group.
    - If there are no fields with threat_level > 0, put all drones to idle.
    - Any drone not needed for the top field's full protection is set to idle.
    - Drones that are moving to a field should be re-assigned to the target's protecting group
      so that they will be considered part of the protection once they arrive (best effort).
    - Ensure every drone is assigned exactly once per call.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Find the field with the highest threat level (> 0)
        top_field = None
        top_threat = 0.0

        for field in environment.fields:
            if getattr(field, "threat_level", 0.0) > top_threat:
                top_threat = float(field.threat_level)
                top_field = field

        # If no threatening field, idle all drones
        if top_field is None or top_threat <= 0.0:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Step 2: Determine the required number of drones for full protection
        required_for_full = 1
        if hasattr(top_field, "drones_for_full_protection"):
            try:
                required_for_full = int(top_field.drones_for_full_protection)
            except Exception:
                required_for_full = 1

        top_group_name = f"protecting {top_field.id}"

        # Step 3: Decide for each drone exactly one target group with a single pass.
        needed = max(0, int(required_for_full))
        assigned_to_top = 0

        for drone in components:
            # If this drone is already protecting the top field, keep it in place
            if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) == top_field.id:
                environment.assign_group(drone, top_group_name)
                assigned_to_top += 1
                continue

            # If we still need more drones for top field protection, assign to that group
            if assigned_to_top < needed:
                environment.assign_group(drone, top_group_name)
                assigned_to_top += 1
                continue

            # Otherwise, idle
            environment.assign_group(drone, "idle")