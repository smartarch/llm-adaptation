import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Always protect the field with the highest threat level (>0) to full protection.
        - If no field has threat level > 0, set all drones to idle.
        - If the top field's protection group isn't listed in group_ids, fall back to idle.
        - Reuse drones already protecting the top field to reach drones_for_full_protection.
        - Any remaining drones become idle.
        """
        top_field = None
        top_threat = -1.0

        for field in environment.fields:
            tl = getattr(field, "threat_level", 0.0)
            if tl > 0 and tl > top_threat:
                top_threat = tl
                top_field = field

        # No field to protect
        if top_field is None:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        top_group_id = f"protecting {top_field.id}"
        if top_group_id not in group_ids:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Drones required for full protection
        required_drones = getattr(top_field, "drones_for_full_protection", None)
        if required_drones is None:
            required_drones = len(components)
        try:
            required_drones = int(required_drones)
        except Exception:
            try:
                required_drones = int(float(required_drones))
            except Exception:
                required_drones = len(components)

        # Count drones currently protecting this field
        assigned = set()
        current_protecting = 0
        for comp in components:
            if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == top_field.id:
                environment.assign_group(comp, top_group_id)
                assigned.add(comp)
                current_protecting += 1

        # Add more drones if needed to reach full protection
        if current_protecting < required_drones:
            needed = required_drones - current_protecting
            for comp in components:
                if comp in assigned:
                    continue
                environment.assign_group(comp, top_group_id)
                assigned.add(comp)
                current_protecting += 1
                needed -= 1
                if needed <= 0:
                    break

        # Remaining drones go idle
        for comp in components:
            if comp not in assigned:
                environment.assign_group(comp, "idle")