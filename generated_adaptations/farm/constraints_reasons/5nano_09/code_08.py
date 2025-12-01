from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map from drone_id to field_id they last protected (or None)
        self._last_protected_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather all fields with positive threat level
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        total_drones = len(components)
        target_protected_count = (total_drones + 1) // 2  # ceil(N/2)

        # If no threats, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
                self._last_protected_by_drone[id(c)] = None
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # Helper to compute field center
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        # Current protection counts by field (based on current state)
        current_protecting_by_field = {fld.id: [] for fld in threatened_fields}
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                tid = c.target_id
                for fld in threatened_fields:
                    if fld.id == tid:
                        current_protecting_by_field[tid].append(c)
                        break

        # Final mapping: drone_id -> group_id (string), to ensure single assignment
        final_group_for_drone = {id(d): None for d in components}
        assigned_ids = set()  # drones assigned in this step

        # Stage 0 (priority): Top-threat field must be fully protected if possible
        top_field = threatened_fields[0]
        top_id = top_field.id
        top_max = int(getattr(top_field, "drones_for_full_protection", 0))
        current_top_list = current_protecting_by_field.get(top_id, [])
        keep = min(len(current_top_list), top_max)

        # Preserve existing protectors of the top field (up to its max)
        for d in current_top_list[:keep]:
            final_group_for_drone[id(d)] = f"protecting {top_id}"
            assigned_ids.add(id(d))
            self._last_protected_by_drone[id(d)] = top_id

        # Need to fill to the top's max
        need_top = top_max - keep
        if need_top > 0:
            # Candidates: all drones not yet assigned in this step
            candidates = [c for c in components if id(c) not in assigned_ids]
            if candidates:
                cx, cy = field_center(top_field)

                def score_top(drone):
                    dx = getattr(drone.location, "x", 0.0) - cx
                    dy = getattr(drone.location, "y", 0.0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                    last = self._last_protected_by_drone.get(id(drone))
                    last_match = 1 if last == top_id else 0
                    return (dist, -last_match)

                candidates.sort(key=score_top)
                chosen = candidates[:need_top]

                for d in chosen:
                    final_group_for_drone[id(d)] = f"protecting {top_id}"
                    assigned_ids.add(id(d))
                    self._last_protected_by_drone[id(d)] = top_id

        # Stage 1: Fill other threatened fields to their max, using closest drones not yet assigned
        for f in threatened_fields[1:]:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))

            current_assigned_to_field = len([
                d for d in components
                if final_group_for_drone.get(id(d)) == f"protecting {field_id}"
            ])
            if current_assigned_to_field >= max_for_field:
                continue

            need = max_for_field - current_assigned_to_field
            if need <= 0:
                continue

            candidates = [c for c in components if id(c) not in assigned_ids]
            if not candidates:
                continue

            cx, cy = field_center(f)

            def score(drone):
                dx = getattr(drone.location, "x", 0.0) - cx
                dy = getattr(drone.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                last = self._last_protected_by_drone.get(id(drone))
                last_match = 1 if last == field_id else 0
                return (dist, -last_match)

            candidates.sort(key=score)
            chosen = candidates[:need]

            for d in chosen:
                final_group_for_drone[id(d)] = f"protecting {field_id}"
                assigned_ids.add(id(d))
                self._last_protected_by_drone[id(d)] = field_id

        # Stage 2: Ensure at least target_protected_count drones are protecting something
        currently_protecting = [
            d for d in components
            if final_group_for_drone.get(id(d)) and final_group_for_drone.get(id(d)).startswith("protecting")
        ]
        total_protected = len(currently_protecting)

        if total_protected < target_protected_count:
            # Fill other fields in threat order
            for f in threatened_fields:
                if total_protected >= target_protected_count:
                    break
                field_id = f.id
                max_for_field = int(getattr(f, "drones_for_full_protection", 0))

                current_for_field = len([d for d in components if final_group_for_drone.get(id(d)) == f"protecting {field_id}"])
                if current_for_field >= max_for_field:
                    continue
                need = min(max_for_field - current_for_field, target_protected_count - total_protected)
                if need <= 0:
                    continue

                candidates = [
                    c for c in components
                    if id(c) not in assigned_ids and final_group_for_drone.get(id(c)) != f"protecting {field_id}"
                ]
                if not candidates:
                    continue

                cx, cy = field_center(f)

                def score2(drone):
                    dx = getattr(drone.location, "x", 0.0) - cx
                    dy = getattr(drone.location, "y", 0.0) - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                    last = self._last_protected_by_drone.get(id(drone))
                    last_match = 1 if last == field_id else 0
                    return (dist, -last_match)

                candidates.sort(key=score2)
                chosen = candidates[:need]

                for d in chosen:
                    final_group_for_drone[id(d)] = f"protecting {field_id}"
                    self._last_protected_by_drone[id(d)] = field_id
                    assigned_ids.add(id(d))
                    total_protected += 1

        # Stage 3: Any drones not assigned to protecting a field become idle
        for c in components:
            if final_group_for_drone.get(id(c)) is None:
                final_group_for_drone[id(c)] = "idle"
                self._last_protected_by_drone[id(c)] = None

        # Apply final assignments (exactly one per drone)
        for c in components:
            target_group = final_group_for_drone.get(id(c), "idle")
            environment.assign_group(c, target_group)