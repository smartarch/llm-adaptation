import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Identify all fields with threat_level > 0 and sort by threat_level descending.
        - Select as many top-threat fields as possible given drones available, but do not move drones unnecessarily.
        - For each selected field, ensure its protecting group has drones up to drones_for_full_protection.
          Reuse drones already protecting that field if possible.
        - Drones are allocated in order of threat; do not move drones unless needed to reach full protection for a field.
        - Any drone not allocated is set to idle.
        - This approach aims to increase protection coverage of the most threatened fields with fewer moves.
        """
        # Gather fields with threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0]

        # If no field to protect, idle all
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort by threat level (desc) for determinism
        fields_with_threat.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        # Precompute available drones
        total_drones = len(components)

        # Identify the set of target fields (top ones we will try to protect)
        # We'll attempt to protect as many top fields as possible, but cap by total drones
        target_fields = []
        allocated_so_far = 0
        for field in fields_with_threat:
            g = f"protecting {field.id}"
            if g not in group_ids:
                continue
            required = getattr(field, "drones_for_full_protection", None)
            if required is None:
                # If not specified, skip this field for protection planning
                continue
            try:
                req = int(required)
            except Exception:
                try:
                    req = int(float(required))
                except Exception:
                    continue
            # If we have no drones left to allocate, stop adding new fields
            if allocated_so_far >= total_drones:
                break
            target_fields.append((field, g, req))
            allocated_so_far += min(req, total_drones)  # rough cap for planning

        # If no target_fields feasible with provided group_ids, fall back to single top field
        if not target_fields:
            top_field = fields_with_threat[0]
            top_group_id = f"protecting {top_field.id}"
            if top_group_id not in group_ids:
                # If cannot protect any field, idle all
                for c in components:
                    environment.assign_group(c, "idle")
                return
            target_fields = [(top_field, top_group_id, getattr(top_field, "drones_for_full_protection", total_drones and int(total_drones)) or total_drones)]

        # Keep track of which drones have been assigned in this step
        assigned = set()

        # Step 1: Reassign drones already protecting any of the target fields to the correct groups
        for comp in components:
            st = getattr(comp, "state", None)
            tgt = getattr(comp, "target_id", None)
            if st == "protecting" and tgt is not None:
                # If this target field is one of our targets, assign to that field's group
                for (field, g, _) in target_fields:
                    if field.id == tgt:
                        environment.assign_group(comp, g)
                        assigned.add(comp)
                        break

        # Step 2: For each target field, ensure its group has required drones, using a pool of unassigned drones
        pool = [c for c in components if c not in assigned]
        for (field, g, req) in target_fields:
            # Current protecting for this field
            current = 0
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                    current += 1
            to_add = max(0, req - current)
            # Move from pool to this field until filled or pool exhausted
            while to_add > 0 and pool:
                c = pool.pop()
                environment.assign_group(c, g)
                assigned.add(c)
                to_add -= 1

        # Step 3: Any remaining drones in pool stay idle
        for c in pool:
            environment.assign_group(c, "idle")