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

        new_assignments = {}

        # If no threat, assign all drones to idle (or preserve last known if valid)
        if not threatened_fields:
            for d in components:
                prev = self.prev_assignments.get(d)
                grp = prev if (prev in group_ids) else "idle"
                new_assignments[d] = grp
        else:
            # Sort threatened fields by threat level (desc)
            threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

            # Build per-field current protectors
            current_by_field = {}
            for f in threatened_fields:
                current = [
                    d for d in components
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
                ]
                current_by_field[f.id] = current

            # Compute shortages
            shortages = []
            for f in threatened_fields:
                target = getattr(f, "drones_for_full_protection", 0)
                shortage = max(0, target - len(current_by_field.get(f.id, [])))
                if shortage > 0:
                    shortages.append((f, shortage))

            assigned = set()

            # Stage 1: allocate to shortages with memory bias
            if shortages:
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

                    taken = 0
                    for d in biased:
                        if taken >= need:
                            break
                        new_assignments[d] = grp
                        assigned.add(d)
                        self.prev_assignments[d] = grp
                        taken += 1

                    if taken < need:
                        remain = need - taken
                        for d in others:
                            if remain <= 0:
                                break
                            new_assignments[d] = grp
                            assigned.add(d)
                            self.prev_assignments[d] = grp
                            remain -= 1

            # Stage 2: If there are drones not yet assigned (no shortages or unfilled),
            # assign any remaining drones to idle to ensure exactly one assignment per drone.
            for d in components:
                if d not in new_assignments:
                    new_assignments[d] = "idle"
                    self.prev_assignments[d] = "idle"

        # Apply final assignments, ensuring valid group names
        for d in components:
            grp = new_assignments.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_assignments[d] = grp