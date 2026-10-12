Reasoning and updated adaptation strategy

Summary of the issue:
- The tests require that the top-threat field is always fully protected with exactly drones_for_full_protection drones, using the closest available drones, and without leaving the top field under-protected due to planning gaps.
- Previous implementations sometimes left the top field short of its required protection due to planning order, continuity biases, or not guaranteeing a single coherent plan per step.

Strategy to fix:
- Build a single, complete plan for all drones in one pass, ensuring every drone is assigned exactly once.
- Explicitly enforce the top-threat field to have exactly drones_for_full_protection drones protecting it:
  - Keep currently protecting drones on that field.
  - Fill the gap with the closest drones that are not already on that field, prioritizing continuity for those drones that previously protected this field.
  - If more drones are protecting the top field than needed, demote the farthest protecting drones to idle to enforce the cap.
- After top field is stabilized, allocate drones to other threatened fields in descending threat level order, again choosing the closest available drones and preferring continuity.
- Finally, assign any remaining drones to idle.
- Maintain a per-drone memory to encourage continuity over time.
- Ensure every drone is assigned exactly once by applying a single plan pass and updating memory accordingly.

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

        # Build set of drones currently protecting top_field
        currently_protecting_top = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id]
        if len(currently_protecting_top) > 0:
            # Ensure we always include these drones in the final plan for top_field
            for d in currently_protecting_top:
                plan[d] = f"protecting {top_field.id}"
                planned_drones.add(id(d))

        # If we need to add more drones to reach required_top
        if current_top < required_top:
            needed_top = required_top - current_top
            # Candidates: any drone not currently protecting top_field
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

        # If we somehow have more protectors than needed, demote farthest ones
        # Compute final top_field protectors in plan
        final_top_protectors = [d for d in components if (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id) or (plan.get(d, None) == f"protecting {top_field.id}")]
        # Remove any that are more than required_top by demoting farthest
        if len(final_top_protectors) > required_top:
            # measure distance to top center
            def d_to_top(d):
                return dist_to_point(d, center_top)
            final_top_protectors.sort(key=d_to_top, reverse=True)  # farthest first
            to_demote = len(final_top_protectors) - required_top
            for i in range(to_demote):
                d = final_top_protectors[i]
                # If it's currently in plan to protect top, remove it from plan
                if plan.get(d, None) == f"protecting {top_field.id}":
                    del plan[d]
                # Mark as idle in plan
                plan[d] = "idle"
                planned_drones.add(id(d))

        # After top field, ensure all other drones assigned to top field are represented in plan
        # Now handle other threatened fields in descending threat order
        for field in threat_fields[1:]:
            center_f = center_of(field)
            current = current_protect_count(field)
            required = int(getattr(field, "drones_for_full_protection", 0))
            needed = max(0, required - current)
            if needed <= 0:
                # If field already fully protected, ensure drones on this field stay
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

        # Finally, ensure every drone is assigned exactly once
        for d in components:
            if id(d) in planned_drones:
                continue
            # If drone is currently protecting something, preserve it
            if getattr(d, "state", None) == "protecting":
                plan[d] = f"protecting {getattr(d, 'target_id', None)}"
                planned_drones.add(id(d))
            else:
                plan[d] = "idle"

        # Apply the plan in a single pass: exactly one assignment per drone
        for d in components:
            group = plan.get(d, "idle")
            environment.assign_group(d, group)
            self.prev_assignment_by_drone[id(d)] = group
```