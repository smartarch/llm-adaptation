Reasoning and adaptation strategy

Strategy overview:
- Objective: always fully protect the field with the highest threat level, using the closest available drones. If that field is already fully protected, keep the drones there and do not overprotect (i.e., avoid assigning more drones than drones_for_full_protection for that field). Use remaining drones to protect other fields only if possible, but avoid partial protection of additional fields unless it leads to fully protected fields.
- Group structure:
  - idle: drones not protecting any field.
  - protect each field with threat > 0 using a group named "protecting {field.id}".
- Drone allocation rules:
  - Always aim to fully protect the top-threat field using the closest drones to that field.
  - After top field is fully protected, consider protecting additional fields in descending threat order, but never exceed each field’s drones_for_full_protection.
  - Maintain at least half of the drones in protection most of the time. If there are spare drones after top-field protection, allocate to next fields to reach at least 50% protected, prioritizing closer drones.
  - To reduce unnecessary drone movement (allocation churn), reuse drones that were protecting a field in the previous step when that field remains the target and still needs protection. This is implemented via a simple memory mechanism that tracks the last assigned group per drone.
- Movement and proximity:
  - Drones are assigned to the closest field (by squared distance to the field center) when extra protection is needed.
  - Drones already assigned to protecting a field or already in proximity to that field have higher priority to stay assigned to that field (to reduce reallocation).
- Implementation notes:
  - Each step, drones are explicitly re-assigned to a group (even if the same as before), as required.
  - Field centers are computed from left, top, right, bottom bounds.
  - The number of drones allocated to each field does not exceed drones_for_full_protection.

Code implementation (Python)

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persistent memory of last assigned group per drone (by id)
        # This helps reduce churn: we try to keep drones on the same field if possible.
        self._last_assignment = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Helpers to check current protection status for a field
        def current_protect_count(field):
            count = 0
            for d in components:
                d_id = id(d)
                last_grp = self._last_assignment.get(d_id, None)
                # Consider a drone protecting this field if:
                # - it was previously assigned to this field, or
                # - it is currently in state 'protecting' and targeting this field
                if last_grp == f"protecting {field.id}":
                    count += 1
                else:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                        count += 1
            return count

        # Helper: is drone currently assigned to protect any field
        def is_protecting_any(d):
            d_id = id(d)
            grp = self._last_assignment.get(d_id, None)
            if grp and grp.startswith("protecting"):
                return True
            if getattr(d, "state", None) == "protecting":
                return True
            return False

        # Sort fields by threat level descending, then by id for determinism
        fields_sorted = sorted(
            fields,
            key=lambda f: (-getattr(f, "threat_level", 0), getattr(f, "id", "")),
        )

        # Prepare centers for distance calculations
        centers = {f.id: center_of(f) for f in fields_sorted}

        total_drones = len(components)
        half_protection = (total_drones + 1) // 2  # at least half

        # We'll build a fresh assignment for this step
        step_assignment = {}

        # Step 1: Ensure the top-threat field is fully protected
        if fields_sorted:
            top = fields_sorted[0]
            needed_top = max(0, getattr(top, "drones_for_full_protection", 0) - current_protect_count(top))
            if needed_top > 0:
                center_top = centers[top.id]

                # Build candidate drones with priority for those already assigned to this field
                candidates = []
                for d in components:
                    d_id = id(d)
                    last_grp = self._last_assignment.get(d_id, None)
                    priority = 0 if (last_grp == f"protecting {top.id}") or (
                        getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id
                    ) else 1
                    lx = getattr(d, "location").x
                    ly = getattr(d, "location").y
                    dist2 = (lx - center_top[0]) ** 2 + (ly - center_top[1]) ** 2
                    candidates.append((priority, dist2, d))
                candidates.sort(key=lambda t: (t[0], t[1]))

                assigned = 0
                for _, _, d in candidates:
                    if assigned >= needed_top:
                        break
                    step_assignment[id(d)] = f"protecting {top.id}"
                    assigned += 1

        # Recompute protected count after attempting top-field protection
        protected_count = sum(1 for d in components if step_assignment.get(id(d), None) == f"protecting {fields_sorted[0].id}" or
                              (getattr(d, "state", None) == "protecting" and fields_sorted and getattr(d, "target_id", None) == fields_sorted[0].id))

        # Step 2: Use remaining drones to protect subsequent fields if we can reach the half-protection goal
        # Only allocate to next fields if we still need to reach at least half the drones in protection
        for f in fields_sorted[1:]:
            if protected_count >= half_protection:
                break
            # How many more drones are needed for full protection of this field
            current = current_protect_count(f)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue

            center_f = centers[f.id]
            candidates = []
            for d in components:
                d_id = id(d)
                last_grp = self._last_assignment.get(d_id, None)
                priority = 0 if (last_grp == f"protecting {f.id}") or (
                    getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
                ) else 1
                lx = getattr(d, "location").x
                ly = getattr(d, "location").y
                dist2 = (lx - center_f[0]) ** 2 + (ly - center_f[1]) ** 2
                candidates.append((priority, dist2, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            assigned = 0
            for _, _, d in candidates:
                if assigned >= needed or protected_count >= half_protection:
                    break
                step_assignment[id(d)] = f"protecting {f.id}"
                assigned += 1
                protected_count += 1

        # Step 3: All remaining drones go idle
        for d in components:
            if id(d) not in step_assignment:
                step_assignment[id(d)] = "idle"

        # Apply the assignments to the environment
        for d in components:
            environment.assign_group(d, step_assignment[id(d)])

        # Persist this step's assignments for the next step
        self._last_assignment = step_assignment
```