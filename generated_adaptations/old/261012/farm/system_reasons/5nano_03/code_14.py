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

        # If no threat, preserve current protection where possible
        if not threatened_fields:
            # Re-assign drones currently protecting to their protecting groups, others to idle
            current_by_field = {f.id: [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id] for f in threatened_fields}
            protecting_any = set()
            for f in threatened_fields:
                grp = f"protecting {f.id}"
                for d in current_by_field.get(f.id, []):
                    environment.assign_group(d, grp)
                    self.prev_assignments[d] = grp
                    protecting_any.add(d)
            for d in components:
                if d not in protecting_any:
                    environment.assign_group(d, "idle")
                    self.prev_assignments[d] = "idle"
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Build per-field current protectors
        current_by_field = {}
        for f in threatened_fields:
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]
            current_by_field[f.id] = current

        # Compute shortages and urgencies
        shortages = []
        for f in threatened_fields:
            target = getattr(f, "drones_for_full_protection", 0)
            shortage = max(0, target - len(current_by_field.get(f.id, [])))
            if shortage > 0:
                shortages.append((f, shortage))

        # If nothing to protect further, preserve current protection and idle the rest
        if not shortages:
            # Re-assign all current protectors to their protecting groups to preserve state
            protecting_any = set()
            for f in threatened_fields:
                grp = f"protecting {f.id}"
                for d in current_by_field.get(f.id, []):
                    environment.assign_group(d, grp)
                    self.prev_assignments[d] = grp
                    protecting_any.add(d)
            for d in components:
                if d not in protecting_any:
                    environment.assign_group(d, "idle")
                    self.prev_assignments[d] = "idle"
            return

        # Sort shortages by urgency: threat_level * shortage
        shortages.sort(key=lambda pair: pair[0].threat_level * pair[1], reverse=True)

        assigned = set()
        # Allocate to each shortage field in order
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
                environment.assign_group(d, grp)
                assigned.add(d)
                self.prev_assignments[d] = grp
                need -= 1

            if need > 0:
                for d in others:
                    if need <= 0:
                        break
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    self.prev_assignments[d] = grp
                    need -= 1

        # Idle remaining drones
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self.prev_assignments[d] = "idle"