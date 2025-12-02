"""
Adaptation reasoning and strategy:

Problem recap:
- We want to minimize field damage by assigning drones to protect fields.
- Each field has a threat_level and a required number of drones for full protection.
- Drones can be assigned to groups "idle" or "protecting {field_id}".
- Previously, the strategy focused on the single most threatened field. This often underutilized drone resources when several fields are worth protecting.

Improved strategy:
- Use a greedy multi-field protection approach.
- Sort all fields with threat_level > 0 by threat descending.
- Allocate drones to fully protect as many of these fields as possible, in that order, using each field's drones_for_full_protection as its quota.
- If drones run out, allocate the remaining drones to partially protect the next field (i.e., assign drones to "protecting {field_id}" even if we cannot reach full protection).
- If no field has threat, send all drones to idle.
- Explicitly re-assign every drone to a group (even if continuing the same action) to satisfy the requirement that components must be reassigned each step.

Benefits:
- Maximizes the number of fully protected high-threat fields.
- Makes best use of limited drones by not wasting resources on less-threatened fields when a higher-threat field still needs protection.
- Still allows partial protection when you cannot fully protect the next field, which is better than no protection.

Implementation notes:
- The plan is computed deterministically: fields are processed in descending threat.
- The final distribution is a simple list of target groups per drone, built from the plan and filled with "idle" for any leftovers.
- This approach respects the required group names and re-assigns all drones every step.

"""

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Distribute drones among fields to maximize protection.
        - Fully protect as many high-threat fields as possible (in threat-descending order).
        - If drones run out, partially protect the next field.
        - If no threats exist, idle all drones.
        """
        # Collect fields with positive threat
        threatening_fields = []
        for f in getattr(environment, "fields", []) or []:
            threat = getattr(f, "threat_level", 0.0)
            try:
                threat_val = float(threat)
            except Exception:
                threat_val = 0.0
            if threat_val > 0.0:
                threatening_fields.append((threat_val, f))

        # If no threatening fields, idle all drones
        if not threatening_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat descending
        threatening_fields.sort(key=lambda tf: tf[0], reverse=True)

        total_drones = len(components)
        targets = []  # list of group names for each drone, in order

        # Allocate drones per field
        for threat_val, field in threatening_fields:
            field_id = getattr(field, "id", None)
            required = int(getattr(field, "drones_for_full_protection", 0))
            if total_drones - len(targets) <= 0:
                break
            if required <= 0:
                continue
            available = total_drones - len(targets)
            allocate = min(required, available)
            for _ in range(allocate):
                targets.append(f"protecting {field_id}")

        # Fill the rest with idle (these drones do not contribute to any protection this step)
        while len(targets) < total_drones:
            targets.append("idle")

        # Assign groups to drones according to the plan
        for c, g in zip(components, targets):
            environment.assign_group(c, g)