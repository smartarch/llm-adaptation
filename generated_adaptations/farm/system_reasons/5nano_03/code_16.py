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
        new_assignments = {}

        # Stage 1: allocate to shortages with memory bias
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
                new_assignments[d] = grp
                self.prev_assignments[d] = grp
                need -= 1

            if need > 0:
                for d in others:
                    if need <= 0:
                        break
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    new_assignments[d] = grp
                    self.prev_assignments[d] = grp
                    need -= 1

        # Stage 2: ensure minimum protection floor (half the drones) if possible
        total_drones = len(components)
        current_protecting_count = sum(1 for d in components if new_assignments.get(d, None).startswith("protecting "))
        half = (total_drones + 1) // 2

        if current_protecting_count < half:
            # Find the best candidate field to add protection to (the most urgent one with capacity)
            # Use the first shortage field if any; if not, skip (to avoid over-protection)
            best_field = None
            best_need = 0
            if shortages:
                best_field, best_need = shortages[0]
                # After initial allocation, recompute the remaining need for this field
                current_after = len([d for d in components if new_assignments.get(d, None) == f"protecting {best_field.id}"])
                best_need = max(0, best_field.drones_for_full_protection - current_after)
            if best_field and best_need > 0:
                grp = f"protecting {best_field.id}"
                pool = [d for d in components if d not in assigned]
                biased = [d for d in pool if self.prev_assignments.get(d) == grp]
                others = [d for d in pool if d not in biased]

                biased.sort(key=lambda d: dist2_to_field_center(d, best_field))
                others.sort(key=lambda d: dist2_to_field_center(d, best_field))

                need = best_need
                for d in biased:
                    if need <= 0:
                        break
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    new_assignments[d] = grp
                    self.prev_assignments[d] = grp
                    need -= 1

                if need > 0:
                    for d in others:
                        if need <= 0:
                            break
                        environment.assign_group(d, grp)
                        assigned.add(d)
                        new_assignments[d] = grp
                        self.prev_assignments[d] = grp
                        need -= 1

        # Stage 3: If there are drones still unassigned, idle them
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