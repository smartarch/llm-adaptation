"""
Greedy marginal-benefit allocation strategy (reduces average damage further):

Idea:
- Treat each drone as a unit of protection that can be allocated to a field.
- At each step, evaluate which threatened field would benefit most from an additional drone.
  Benefit is approximated by threat_level divided by remaining drones needed to fully protect the field.
- Always favor the top-threat field first, but if it is already fully protected, allocate to the next-best field by the same rule.
- Use the closest available drone to the target field to minimize travel time and accelerate protection.
- Drones already assigned to protect a field remain there (no reversion in a single tick), and we ensure every drone is assigned exactly once.

Notes:
- We account for current protection for every field using: protecting_drones + arriving_drones + drones already assigned to that field via final mapping.
- If there are no threatened fields, all drones go idle.
"""

from math import hypot

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Collect threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Step 2: Sort threatened fields by threat level (high to low)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        # Step 3: Maintain a final mapping (one group per drone)
        final_group = {}
        def assign(d, grp):
            if d not in final_group:
                final_group[d] = grp

        # Step 4: Pre-assign drones already heading to the top field
        top_field = threatened[0]
        top_id = top_field.id
        for c in components:
            st = getattr(c, "state", "")
            tid = getattr(c, "target_id", None)
            if tid == top_id and st in ("moving_to_field", "protecting"):
                assign(c, f"protecting {top_id}")

        # Helper to compute current protection for a given field
        def current_protection(field):
            fid = field.id
            cur = getattr(field, "protecting_drones", 0) + getattr(field, "arriving_drones", 0)
            cur += sum(1 for d, g in final_group.items() if g == f"protecting {fid}")
            return cur

        # Step 5: Greedily allocate drones to improve protection
        # We'll repeatedly assign the closest available drone to the field that provides the best marginal benefit.
        # The process stops when no field needs more drones or no unassigned drones remain.
        while True:
            # Evaluate best field to assign one more drone to
            best_field = None
            best_score = 0.0
            best_need = 0
            for f in threatened:
                fid = f.id
                full = int(getattr(f, "drones_for_full_protection", 1))
                need = max(0, full - current_protection(f))
                if need > 0:
                    # Marginal value estimate: higher threat and larger remaining need implies higher priority
                    score = getattr(f, "threat_level", 0.0) / max(1, need)
                    if score > best_score:
                        best_score = score
                        best_field = f
                        best_need = need

            if best_field is None:
                break  # all fields fully protected or no drones left to assign

            # Find the closest available drone to the best_field center
            cx = (getattr(best_field, "left", 0) + getattr(best_field, "right", 0)) / 2.0
            cy = (getattr(best_field, "top", 0) + getattr(best_field, "bottom", 0)) / 2.0

            closest = None
            closest_dist = None
            for c in components:
                if c in final_group:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                d = hypot(getattr(loc, "x", 0.0) - cx, getattr(loc, "y", 0.0) - cy)
                if closest_dist is None or d < closest_dist:
                    closest = c
                    closest_dist = d

            if closest is None:
                break  # no more drones available to assign

            assign(closest, f"protecting {best_field.id}")

        # Step 6: Ensure every drone is assigned to a group (idle if not assigned)
        for c in components:
            if c not in final_group:
                final_group[c] = "idle"

        # Step 7: Apply assignments
        for c, grp in final_group.items():
            environment.assign_group(c, grp)