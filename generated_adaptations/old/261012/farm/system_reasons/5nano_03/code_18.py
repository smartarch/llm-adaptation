from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of last assignment per drone to encourage stability
        # Key: drone object, Value: group_id string from last step
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper: field center
        def field_center(field):
            cx = (field.left + field.right) * 0.5
            cy = (field.top + field.bottom) * 0.5
            return cx, cy

        # Helper: squared distance from drone to field center
        def dist2_to_field_center(drone, field):
            cx, cy = field_center(field)
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return dx * dx + dy * dy

        # If no threat, assign all drones to idle (or preserve current protection via memory)
        if not threatened_fields:
            new_assignments = {}
            # Preserve current protection whenever possible
            for d in components:
                # If we have memory suggesting a protecting group for this drone, try to reuse it
                prev = self.prev_assignments.get(d)
                if prev is not None and prev in group_ids:
                    new_assignments[d] = prev
                else:
                    new_assignments[d] = "idle"
            # Apply exactly once per drone
            for d in components:
                grp = new_assignments.get(d, "idle")
                if grp not in group_ids:
                    grp = "idle"
                environment.assign_group(d, grp)
                self.prev_assignments[d] = grp
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Build per-field current protectors
        current_by_field = {}
        for f in threatened_fields:
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]
            current_by_field[f.id] = current

        # Compute shortages
        shortages = []
        for f in threatened_fields:
            target = getattr(f, "drones_for_full_protection", 0)
            shortage = max(0, target - len(current_by_field.get(f.id, [])))
            if shortage > 0:
                shortages.append((f, shortage))

        new_assignments = {}
        assigned = set()

        if shortages:
            # Stage 1: allocate to shortages with memory bias
            shortages.sort(key=lambda pair: pair[0].threat_level * pair[1], reverse=True)
            for f, need in shortages:
                if need <= 0:
                    continue
                grp = f"protecting {f.id}"
                pool = [d for d in components if d not in assigned]

                # Bias: prefer drones previously assigned to this field
                biased = [d for d in pool if self.prev_assignments.get(d) == grp]
                others = [d for d in pool if d not in biased]

                biased.sort(key=lambda d: dist2_to_field_center(d, f))
                others.sort(key=lambda d: dist2_to_field_center(d, f))

                # Assign from biased first, then others
                for d in biased:
                    if need <= 0:
                        break
                    new_assignments[d] = grp
                    assigned.add(d)
                    self.prev_assignments[d] = grp
                    need -= 1

                if need > 0:
                    for d in others:
                        if need <= 0:
                            break
                        new_assignments[d] = grp
                        assigned.add(d)
                        self.prev_assignments[d] = grp
                        need -= 1

        # Stage 2: If there are drones left (no shortages or unfilled), optionally keep some stability
        # For simplicity and to ensure the "one assignment per drone" rule, if there are no shortages,
        # we will preserve current protectors and idle the rest.
        if not shortages:
            # Preserve current protectors on their existing groups
            for f in threatened_fields:
                grp = f"protecting {f.id}"
                for d in current_by_field.get(f.id, []):
                    new_assignments[d] = grp
                    assigned.add(d)

            # Any drone not assigned yet becomes idle
            for d in components:
                if d not in assigned:
                    new_assignments[d] = "idle"
                    self.prev_assignments[d] = "idle"
            # Apply below
        else:
            # Stage 3: Assign remaining drones to idle if not already assigned
            for d in components:
                if d not in assigned and d not in new_assignments:
                    new_assignments[d] = "idle"

        # Apply assignments (exactly once per drone)
        for d in components:
            grp = new_assignments.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_assignments[d] = grp