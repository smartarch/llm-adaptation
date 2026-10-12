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

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helpers
        def field_center(field):
            cx = (field.left + field.right) * 0.5
            cy = (field.top + field.bottom) * 0.5
            return cx, cy

        def dist2_to_field_center(drone, field):
            cx, cy = field_center(field)
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return dx * dx + dy * dy

        total_drones = len(components)
        assigned = set()
        new_assignments = {}  # temporary mapping for this step

        # Current protectors per field (for reference)
        current_protectors_by_field = {}
        for f in threatened_fields:
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]
            current_protectors_by_field[f.id] = current

        # PROTECT TOP FIELD FIRST
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        target_top = getattr(top_field, "drones_for_full_protection", 0)

        current_top = current_protectors_by_field.get(top_field.id, [])

        # If over-protected, move extras farthest to idle
        if len(current_top) > max(target_top, 0):
            current_top.sort(key=lambda d: dist2_to_field_center(d, top_field), reverse=True)
            extras = current_top[: len(current_top) - max(target_top, 0)]
            for d in extras:
                new_assignments[d] = "idle"
                assigned.add(d)
            current_top = current_top[len(current_top) - max(target_top, 0):]

        # If we need more drones for top field, allocate closest drones (with memory bias)
        need_top = max(0, max(target_top, 0) - len(current_top))
        if need_top > 0:
            # Candidates are drones not yet assigned in this step
            candidates = [d for d in components if d not in assigned]
            # Memory bias: prefer those previously assigned to top_group
            memory_pref = [d for d in candidates if self.prev_assignments.get(d) == top_group]
            non_memory = [d for d in candidates if d not in memory_pref]

            # Sort by distance to top field
            memory_pref.sort(key=lambda d: dist2_to_field_center(d, top_field))
            non_memory.sort(key=lambda d: dist2_to_field_center(d, top_field))

            for d in memory_pref:
                if need_top <= 0:
                    break
                new_assignments[d] = top_group
                assigned.add(d)
                current_top.append(d)
                need_top -= 1

            if need_top > 0:
                for d in non_memory:
                    if need_top <= 0:
                        break
                    new_assignments[d] = top_group
                    assigned.add(d)
                    current_top.append(d)
                    need_top -= 1

        # Assign remaining fields in threat order
        for f in threatened_fields[1:]:
            field_group = f"protecting {f.id}"
            target = getattr(f, "drones_for_full_protection", 0)

            current = current_protectors_by_field.get(f.id, [])
            # If over-protected, move extras farthest to idle
            if len(current) > max(target, 0):
                current.sort(key=lambda d: dist2_to_field_center(d, f), reverse=True)
                extras = current[: len(current) - max(target, 0)]
                for d in extras:
                    new_assignments[d] = "idle"
                    assigned.add(d)
                current = current[len(current) - max(target, 0):]

            need = max(0, max(target, 0) - len(current))
            if need > 0:
                pool = [d for d in components if d not in assigned]
                # Memory bias: prefer drones previously protecting this field
                memory_pref = [d for d in pool if self.prev_assignments.get(d) == field_group]
                non_memory = [d for d in pool if d not in memory_pref]

                memory_pref.sort(key=lambda d: dist2_to_field_center(d, f))
                non_memory.sort(key=lambda d: dist2_to_field_center(d, f))

                for d in memory_pref:
                    if need <= 0:
                        break
                    new_assignments[d] = field_group
                    assigned.add(d)
                    current.append(d)
                    need -= 1

                if need > 0:
                    for d in non_memory:
                        if need <= 0:
                            break
                        new_assignments[d] = field_group
                        assigned.add(d)
                        current.append(d)
                        need -= 1

        # Finally, any unassigned drones go idle
        for d in components:
            if d not in assigned and d not in new_assignments:
                new_assignments[d] = "idle"

        # Apply assignments and update memory
        for d in components:
            grp = new_assignments.get(d, "idle")
            # Ensure the group name is valid (safety)
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_assignments[d] = grp