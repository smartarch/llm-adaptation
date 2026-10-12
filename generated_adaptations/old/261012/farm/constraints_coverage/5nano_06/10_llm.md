Reasoning and updated adaptation strategy

- What changed:
  - The tests now require that drones are not assigned to protect more than a field’s drones_for_full_protection (no overprotection).
  - Drones protecting the most-threatened field should be the closest ones, and we should prioritize fully protecting that single top field when possible.
  - Additionally, we should aim to utilize at least half of the drones in protection most of the time, but without violating per-field protection limits. We fulfill this by allocating additional closest idle drones to fields (starting with the top field and then other threatened fields) only up to their needs and until the half-protection target is reached.

- How the strategy works now:
  1) Identify the field with the highest threat (top_field) and its need (drones_for_full_protection).
  2) Reallocate drones currently protecting the top_field to ensure it reaches its full protection quota using the closest available drones.
  3) If, after Step 2, fewer than half of the drones are protecting any field, allocate additional closest idle drones to fields (starting from the top field and then other threatened fields) up to each field’s need until we reach at least half of the fleet protecting.
  4) Finally, assign all remaining drones to idle.
  5) Ensure every drone is assigned exactly once by computing a single target group per drone and applying all assignments in one pass.

- Why this fixes the failures:
  - It prevents overprotection by never assigning more than drones_for_full_protection to any field.
  It uses the closest drones to the top field for initial protection, as required, and fills remaining protection needs from idle drones in order to meet the half-protection constraint without exceeding field needs.

Python code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]

        # Drones needed for full protection of the top field
        needs = {f.id: int(getattr(f, "drones_for_full_protection", len(components))) for f in threat_fields}

        # Build current protectors per field
        current_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]

        target_group = {d: None for d in components}
        protecting_set = set(current_top)

        # Mark existing protectors for top
        for d in current_top:
            target_group[d] = f"protecting {top_field.id}"

        # Step A: fill top field to its full protection with closest drones
        needed = needs[top_field.id]
        to_add = max(0, needed - len(current_top))
        if to_add > 0:
            center_x = (top_field.left + top_field.right) / 2.0
            center_y = (top_field.top + top_field.bottom) / 2.0

            def dist_to_top(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float('inf')
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx*dx + dy*dy

            candidates = [d for d in components if d not in protecting_set]
            candidates.sort(key=dist_to_top)

            for d in candidates[:to_add]:
                target_group[d] = f"protecting {top_field.id}"
                protecting_set.add(d)

        # Step B: ensure at least half of drones are protecting, using remaining idle drones first, across all fields
        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        def count_protecting():
            return sum(1 for d in components if target_group[d] is not None and target_group[d].startswith("protecting"))

        protecting_count = count_protecting()
        if protecting_count < half_target:
            # For each field, try to fill remaining needs from closest idle drones
            for f in threat_fields:
                fid = f.id
                current_for_field = sum(1 for d in components if target_group[d] == f"protecting {fid}")
                remaining = max(0, needs[fid] - current_for_field)
                if remaining <= 0:
                    continue

                center_x = (f.left + f.right) / 2.0
                center_y = (f.top + f.bottom) / 2.0

                def dist_to_field(d):
                    loc = getattr(d, "location", None)
                    if loc is None:
                        return float('inf')
                    dx = loc.x - center_x
                    dy = loc.y - center_y
                    return dx*dx + dy*dy

                idle_drones = [d for d in components if target_group[d] is None]
                idle_drones.sort(key=dist_to_field)

                for d in idle_drones[:remaining]:
                    target_group[d] = f"protecting {fid}"
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Step C: any remaining drones go idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Final: assign exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])
```