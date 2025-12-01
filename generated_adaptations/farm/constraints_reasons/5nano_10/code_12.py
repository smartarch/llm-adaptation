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

        # Top field handling (strict stabilization)
        top_field = threat_fields[0]
        center_top = center_of(top_field)
        current_top = current_protect_count(top_field)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Include drones currently protecting the top field
        currently_protecting_top = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]
        for d in currently_protecting_top:
            plan[d] = f"protecting {top_field.id}"
            planned_drones.add(id(d))

        # If we have more than required_top protectors, demote farthest ones
        if len(currently_protecting_top) > required_top and required_top > 0:
            # Distances to top center
            def dist_to_top(d):
                return dist_to_point(d, center_top)
            # Farthest first
            sorted_protectors = sorted(currently_protecting_top, key=dist_to_top, reverse=True)
            to_demote = len(currently_protecting_top) - required_top
            for i in range(min(to_demote, len(sorted_protectors))):
                d = sorted_protectors[i]
                # Remove any prior plan if present
                if plan.get(d) == f"protecting {top_field.id}":
                    del plan[d]
                plan[d] = "idle"
                planned_drones.add(id(d))

        # If we have fewer than required_top protectors, fill with closest available
        if len([d for d in currently_protecting_top if d is not None and plan.get(d) != "idle"]) < required_top:
            need = max(0, required_top - len([d for d in currently_protecting_top]))
            candidates = []
            for d in components:
                # skip drones already protecting the top
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                dd = dist_to_point(d, center_top)
                prev_group = self.prev_assignment_by_drone.get(id(d), None)
                prefer = 1 if prev_group == f"protecting {top_field.id}" else 0
                candidates.append((dd, -prefer, d))
            candidates.sort(key=lambda t: (t[0], t[1]))
            for dist_val, negpref, d in candidates:
                if need <= 0:
                    break
                plan[d] = f"protecting {top_field.id}"
                planned_drones.add(id(d))
                need -= 1

        # After stabilizing top field, ensure we do not exceed planned count
        # (We rely on the explicit demotion above to enforce the cap.)

        # Handle other threatened fields in descending threat order
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