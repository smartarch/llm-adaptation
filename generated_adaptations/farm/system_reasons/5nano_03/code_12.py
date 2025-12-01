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

        # If no threat, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_assignments[d] = "idle"
            return

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

        # Build per-field current protectors and shortages
        field_info = []  # list of tuples (field, shortage)
        for f in threatened_fields:
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]
            target = getattr(f, "drones_for_full_protection", 0)
            shortage = max(0, target - len(current))
            field_info.append((f, shortage))

        # Shortages only list
        shortages = [(f, s) for (f, s) in field_info if s > 0]

        # If nothing to shortage, just idle all (or keep existing protection, but we assign explicitly)
        if not shortages:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_assignments[d] = "idle"
            return

        # Sort shortages by urgency: higher (threat_level * shortage) first
        shortages.sort(key=lambda fs: (fs[0].threat_level * fs[1]), reverse=True)

        assigned = set()
        new_assignments = {}

        # Allocate to each shortage field in order
        for f, need in shortages:
            if need <= 0:
                continue
            group_id = f"protecting {f.id}"
            # Pool of available drones (not yet assigned in this step)
            pool = [d for d in components if d not in assigned]

            # Bias: prefer drones previously assigned to this field
            biased = [d for d in pool if self.prev_assignments.get(d) == group_id]
            others = [d for d in pool if d not in biased]

            # Sort by distance to the field
            biased.sort(key=lambda d: dist2_to_field_center(d, f))
            others.sort(key=lambda d: dist2_to_field_center(d, f))

            # Assign from biased first, then others
            for d in biased:
                if need <= 0:
                    break
                new_assignments[d] = group_id
                assigned.add(d)
                need -= 1

            if need > 0:
                for d in others:
                    if need <= 0:
                        break
                    new_assignments[d] = group_id
                    assigned.add(d)
                    need -= 1

        # After fulfilling shortages, assign remaining drones to idle
        for d in components:
            if d not in assigned and d not in new_assignments:
                new_assignments[d] = "idle"

        # Apply assignments and update memory
        for d in components:
            grp = new_assignments.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_assignments[d] = grp