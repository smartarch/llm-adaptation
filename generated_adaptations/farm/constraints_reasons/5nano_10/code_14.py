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

        # If no fields or no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_assignment_by_drone[id(d)] = "idle"
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

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

        # Build a single coherent plan: drone -> group
        plan = {}
        used = set()

        # Top field stabilization (strict)
        top_field = threat_fields[0]
        top_center = center_of(top_field)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Compute a score for each drone to prefer:
        # - closer distance to top center
        # - continuity: prefer drones that previously protected this top field
        candidates = []
        for d in components:
            dd = dist_to_point(d, top_center)
            prev_group = self.prev_assignment_by_drone.get(id(d), None)
            continuity = 1 if prev_group == f"protecting {top_field.id}" else 0
            candidates.append((dd, -continuity, d))
        candidates.sort(key=lambda t: (t[0], t[1]))

        top_protectors = []
        for dist_val, negcont, d in candidates:
            if len(top_protectors) >= max(0, required_top):
                break
            top_protectors.append(d)

        # Assign top field protectors
        for d in top_protectors:
            plan[d] = f"protecting {top_field.id}"
            used.add(id(d))

        # If there are not enough drones to reach required_top, we will keep as many as possible.
        # Allocate remaining drones to other fields in threat order
        remaining_fields = threat_fields[1:]

        for field in remaining_fields:
            center = center_of(field)
            required = int(getattr(field, "drones_for_full_protection", 0))

            # Count how many drones are already planning to protect this field
            current_in_plan = sum(1 for g in plan.values() if g == f"protecting {field.id}")

            needed = max(0, required - current_in_plan)

            if needed <= 0:
                # If some drones were planning to protect this field (or it already has protection), keep them
                for d in components:
                    if plan.get(d) == f"protecting {field.id}":
                        used.add(id(d))
                        # ensure every such drone is recorded
                        pass
                continue

            # Build a candidate list from drones not yet used
            candidates = []
            for d in components:
                if id(d) in used:
                    continue
                dd = dist_to_point(d, center)
                prev_group = self.prev_assignment_by_drone.get(id(d), None)
                continuity = 1 if prev_group == f"protecting {field.id}" else 0
                candidates.append((dd, -continuity, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            for dist_val, negcont, d in candidates:
                if needed <= 0:
                    break
                plan[d] = f"protecting {field.id}"
                used.add(id(d))
                needed -= 1

        # Finally, assign any drones not in plan to idle
        for d in components:
            if id(d) not in {id(x) for x in plan.keys()}:
                plan[d] = "idle"

        # Apply the plan in a single pass
        for d in components:
            group = plan.get(d, "idle")
            environment.assign_group(d, group)
            self.prev_assignment_by_drone[id(d)] = group