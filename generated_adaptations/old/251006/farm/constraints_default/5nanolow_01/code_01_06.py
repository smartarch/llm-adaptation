import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Identify all fields with threat_level > 0 and sort them by threat_level descending.
        - Always fully protect the field with the highest threat_level (top_field) using its
          drones_for_full_protection. Reuse existing drones already protecting it.
        - Use any remaining drones to start protecting other high-threat fields (in order),
          up to each field's drones_for_full_protection. Do not violate available drones.
        - Any drones not allocated to a protection group are assigned to idle.
        """
        # Gather fields with threat
        fields_with_threat = []
        for field in environment.fields:
            tl = getattr(field, "threat_level", 0.0)
            if tl > 0:
                fields_with_threat.append(field)
        # If no field to protect
        if not fields_with_threat:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort by threat level desc for determinism
        fields_with_threat.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        top_field = fields_with_threat[0]
        top_group_id = f"protecting {top_field.id}"
        # If the top group isn't allowed, fallback to idle
        if top_group_id not in group_ids:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Ensure top field protection group is assigned to those drones that protect it
        required_top = getattr(top_field, "drones_for_full_protection", None)
        if required_top is None:
            required_top = len(components)
        try:
            required_top = int(required_top)
        except Exception:
            try:
                required_top = int(float(required_top))
            except Exception:
                required_top = len(components)

        assigned = set()
        current_protecting_top = 0
        # Reassign drones already protecting top field to the top group
        for comp in components:
            if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == top_field.id:
                environment.assign_group(comp, top_group_id)
                assigned.add(comp)
                current_protecting_top += 1

        # If not enough, allocate from unassigned drones to top field
        if current_protecting_top < required_top:
            needed = required_top - current_protecting_top
            for comp in components:
                if comp in assigned:
                    continue
                environment.assign_group(comp, top_group_id)
                assigned.add(comp)
                current_protecting_top += 1
                needed -= 1
                if needed <= 0:
                    break

        # Build a pool of remaining drones not yet assigned to any group in this step
        pool = [comp for comp in components if comp not in assigned]

        # Allocate to other threatened fields in order, up to their required protection
        for field in fields_with_threat[1:]:
            group_id = f"protecting {field.id}"
            if group_id not in group_ids:
                continue
            required_for_field = getattr(field, "drones_for_full_protection", None)
            if required_for_field is None:
                continue
            try:
                required_for_field = int(required_for_field)
            except Exception:
                try:
                    required_for_field = int(float(required_for_field))
                except Exception:
                    continue
            # Current protecting drones for this field
            current_for_field = 0
            for comp in components:
                if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == field.id:
                    current_for_field += 1
            to_assign = max(0, required_for_field - current_for_field)

            while to_assign > 0 and pool:
                c = pool.pop()
                environment.assign_group(c, group_id)
                assigned.add(c)
                to_assign -= 1

        # Remaining drones (in pool) go idle
        for comp in pool:
            environment.assign_group(comp, "idle")