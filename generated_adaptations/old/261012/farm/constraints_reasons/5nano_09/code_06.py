from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map from drone_id (id(drone)) to field_id they last protected (or None)
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

        # Stage 0: Keep current protectors as much as possible, up to max_for_field
        for f in threatened_fields:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))
            current_list = current_protecting_by_field.get(field_id, [])
            current_count = len(current_list)

            keep_count = min(current_count, max_for_field)
            for d in current_list[:keep_count]:
                final_group_for_drone[id(d)] = f"protecting {field_id}"
                self._last_protected_by_drone[id(d)] = field_id
                assigned_ids.add(id(d))

        # Stage 1: Fill each threatened field to its max_for_field using closest drones not yet assigned
        for f in threatened_fields:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))

            # Count how many are already assigned to protect this field in this step
            current_assigned_to_field = len([
                d for d in components
                if final_group_for_drone.get(id(d)) == f"protecting {field_id}"
            ])
            if current_assigned_to_field >= max_for_field:
                continue

            need = max_for_field - current_assigned_to_field
            if need <= 0:
                continue

            # Candidates: drones not yet assigned in this step (in assigned_ids)
            candidates = [
                c for c in components
                if id(c) not in assigned_ids and final_group_for_drone.get(id(c)) != f"protecting {field_id}"
            ]
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
                self._last_protected_by_drone[id(d)] = field_id
                assigned_ids.add(id(d))

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

                # Current number protecting this field (in final plan)
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