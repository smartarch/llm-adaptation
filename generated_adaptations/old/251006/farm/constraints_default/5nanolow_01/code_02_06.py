import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Always attempt to fully protect as many of the top-threat fields as possible using their
          dedicated protection groups, starting with the most threatened.
        - First, guarantee the top-threat field is fully protected by moving drones (from anywhere)
          to its group until drones_for_full_protection is reached.
        - Then, iteratively allocate additional drones to the next most-threatened fields (in order)
          until their own drones_for_full_protection is reached or we run out of drones.
        - Any remaining drones stay idle.
        - This reduces movement overhead and improves coverage on the most threatened fields.
        """
        # Collect fields with threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0]
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort by threat (desc) for determinism
        fields_with_threat.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        total_drones = len(components)

        # Prepare: determine target fields with their groups and required counts
        targets = []
        for field in fields_with_threat:
            g = f"protecting {field.id}"
            if g in group_ids:
                req = getattr(field, "drones_for_full_protection", None)
                if req is None:
                    continue
                try:
                    req = int(req)
                except Exception:
                    try:
                        req = int(float(req))
                    except Exception:
                        continue
                targets.append((field, g, req))

        if not targets:
            # If nothing feasible, idle all
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Track assignments
        assigned = set()
        current_top = 0
        top_field, top_group_id, top_required = targets[0]

        # Step 1: Reuse drones already protecting top_field
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                environment.assign_group(c, top_group_id)
                assigned.add(c)
                current_top += 1

        # Step 2: Move additional drones to top_field to reach full protection
        if current_top < top_required:
            needed = top_required - current_top
            for c in components:
                if c in assigned:
                    continue
                environment.assign_group(c, top_group_id)
                assigned.add(c)
                current_top += 1
                needed -= 1
                if needed <= 0:
                    break

        # Step 3: Allocate to other high-threat fields using remaining drones
        pool = [c for c in components if c not in assigned]

        for field, g, req in targets[1:]:
            # Current protecting for this field
            current = 0
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id:
                    current += 1
            to_add = max(0, req - current)
            while to_add > 0 and pool:
                c = pool.pop()
                environment.assign_group(c, g)
                assigned.add(c)
                to_add -= 1
                current += 1

        # Step 4: Remaining drones go idle
        for c in pool:
            environment.assign_group(c, "idle")