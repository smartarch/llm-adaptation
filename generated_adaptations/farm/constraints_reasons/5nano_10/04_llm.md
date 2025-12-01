Reasoning and updated adaptation strategy

What went wrong and how we fix it:
- The previous implementation sometimes assigned the same drone multiple times in different steps, violating the “exactly once” requirement. The root cause was applying multiple independent assignment passes and re-assigning drones in multiple loops.
- We fix this by building a single, complete plan mapping every drone to exactly one target group (either "protecting {field_id}" or "idle") and then applying all assignments in one pass.
- We also improve robustness to over-protection: if a field already has full protection, we explicitly keep exactly drones_for_full_protection drones protecting that field and move any extra drones away (idle). If there are fewer than needed drones, we fill with the closest available drones, prioritizing continuity (prefer drones that previously protected this field).
- We allocate drones in a priority order: top-threat field first, then other threatened fields in descending threat level. This ensures the most threatened field is always fully protected when possible, while avoiding over-allocation to many fields.
- We preserve continuity by favoring drones that previously protected the same field when choosing candidates.

What changed:
- Build a single plan dict mapping each drone to a target group.
- Handle the top field case carefully: keep exact drones needed for full protection (or reassign extras away), and only then consider other fields.
- Assign every drone exactly once in one pass, updating a persistent per-drone memory to improve continuity over time.

Code (Python)

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember last group assignment for each drone (keyed by id(component))
        self.prev_assignment_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields and identify those with threat > 0
        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute field center
        def center_of(field):
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        # Helper to compute distance from drone to a point
        def dist_to_point(drone, pt):
            dx = drone.location.x - pt[0]
            dy = drone.location.y - pt[1]
            return (dx * dx + dy * dy) ** 0.5

        # If no fields or no threats, idle all drones
        if not threat_fields:
            plan = {}
            for d in components:
                plan[d] = "idle"
            for d in components:
                environment.assign_group(d, plan[d])
                self.prev_assignment_by_drone[id(d)] = plan[d]
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Build plan: drone -> target group
        plan = {}
        planned_drones = set()

        # Helper: current protection count for a field
        def current_protect_count(field):
            count = 0
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    count += 1
            return count

        # Top field handling
        top_field = threat_fields[0]
        center_top = center_of(top_field)
        current_top = current_protect_count(top_field)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # If already over-protected, move extras away
        if current_top > required_top and required_top > 0:
            # Move farthest drones away first (to idle)
            # Gather drones currently protecting the top field
            protecting_top = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id]
            # Sort by distance to center_top descending (farthest first)
            protecting_top.sort(key=lambda d: dist_to_point(d, center_top), reverse=True)
            extras_to_move = current_top - required_top
            for i in range(min(extras_to_move, len(protecting_top))):
                d = protecting_top[i]
                plan[d] = "idle"
                planned_drones.add(id(d))

        # If not enough protectors yet, assign additional drones to top field
        if current_top <= required_top:
            needed_top = max(0, required_top - current_top)
            if needed_top > 0:
                candidates = []
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                        continue
                    dd = dist_to_point(d, center_top)
                    prev_group = self.prev_assignment_by_drone.get(id(d), None)
                    prefer = 1 if prev_group == f"protecting {top_field.id}" else 0
                    candidates.append((dd, -prefer, d))
                candidates.sort(key=lambda t: (t[0], t[1]))
                for dist_val, negpref, d in candidates:
                    if needed_top <= 0:
                        break
                    plan[d] = f"protecting {top_field.id}"
                    planned_drones.add(id(d))
                    needed_top -= 1

        # Handle other threatened fields in descending threat order
        for field in threat_fields[1:]:
            center_f = center_of(field)
            current = current_protect_count(field)
            required = int(getattr(field, "drones_for_full_protection", 0))
            needed = max(0, required - current)
            if needed <= 0:
                # If field already fully protected, ensure currently protecting drones stay
                if current > 0:
                    for d in components:
                        if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                            plan[d] = f"protecting {field.id}"
                            planned_drones.add(id(d))
                continue

            candidates = []
            for d in components:
                if id(d) in planned_drones:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    continue
                dd = dist_to_point(d, center_f)
                prev_group = self.prev_assignment_by_drone.get(id(d), None)
                prefer = 1 if prev_group == f"protecting {field.id}" else 0
                candidates.append((dd, -prefer, d))
            candidates.sort(key=lambda t: (t[0], t[1]))
            for dist_val, negpref, d in candidates:
                if needed <= 0:
                    break
                plan[d] = f"protecting {field.id}"
                planned_drones.add(id(d))
                needed -= 1

        # Finally, any drones not in plan become idle
        for d in components:
            if id(d) not in planned_drones:
                plan[d] = "idle"

        # Apply the plan in a single pass: exactly one assignment per drone
        for d in components:
            group = plan.get(d, "idle")
            environment.assign_group(d, group)
            self.prev_assignment_by_drone[id(d)] = group
```