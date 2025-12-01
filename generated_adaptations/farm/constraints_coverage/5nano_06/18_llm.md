Reasoning and updated adaptation strategy

- Goal of the update:
  - Guarantee that the most threatened field (the top_field) is always fully protected when possible, using the closest drones.
  - Do not overprotection: do not assign more drones to any field than its drones_for_full_protection.
  - After securing the top field, fill additional protection up to at least half the fleet if possible, by allocating the closest idle drones to threatened fields in threat order.
  - Ensure every drone is assigned exactly once in a single decision pass.

- Key changes in the strategy:
  - Step 1: Explicitly allocate the top_field to its full protection quota using the closest drones from the entire fleet, regardless of previous assignments. This guarantees the top-field protection at the first step.
  - Step 2: If fewer than half of drones are protecting any field, allocate additional closest idle drones to fields (in threat order) up to each field’s need, until we reach at least half of the fleet protecting.
  - Step 3: Any remaining drones become idle.
  - All drones are assigned exactly once.

- Why this fixes the failure:
  - It ensures the most threatened field (top_field) is always fully protected as a priority in Step 1, addressing the failing case where 0 drones were assigned to the top field despite its high threat.

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

        # Drones needed for full protection for each field
        needs = {f.id: int(getattr(f, "drones_for_full_protection", len(components))) for f in threat_fields}

        # Build the target mapping: which group each drone should belong to
        target_group = {d: None for d in components}

        # Helper: compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance squared from a drone to a field center
        def dist2_to(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # Step 1: Fully protect the top field using the closest drones
        top_needed = needs[top_field.id]
        top_center_x, top_center_y = center_of(top_field)

        # Sort all drones by distance to the top field center
        all_drones_sorted = sorted(components, key=lambda d: dist2_to(d, top_center_x, top_center_y))
        top_drones = all_drones_sorted[:min(top_needed, len(components))]

        for d in top_drones:
            target_group[d] = f"protecting {top_field.id}"

        # Step 2: If fewer than half the drones are protecting, fill with closest idle drones across threatened fields
        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        def current_protecting_count():
            return sum(1 for d in components if target_group[d] is not None and target_group[d].startswith("protecting"))

        protecting_count = current_protecting_count()

        if protecting_count < half_target:
            # Fill needs starting from the top field and then others
            for f in threat_fields:
                fid = f.id
                center_x, center_y = center_of(f)
                current_for_field = sum(1 for d in components if target_group[d] == f"protecting {fid}")
                remaining = max(0, needs[fid] - current_for_field)
                if remaining <= 0:
                    continue

                idle_candidates = [d for d in components if target_group[d] is None]
                idle_candidates.sort(key=lambda d: dist2_to(d, center_x, center_y))

                for d in idle_candidates[:remaining]:
                    target_group[d] = f"protecting {fid}"
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Step 3: Any drone not assigned yet becomes idle
        for d in components:
            if target_group[d] is None:
                target_group[d] = "idle"

        # Final assignment: exactly one group per drone
        for d in components:
            environment.assign_group(d, target_group[d])
```