from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map from drone_id (id(component)) to field_id they last protected (or None)
        self._last_protected_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather all fields with positive threat level
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        total_drones = len(components)
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

        # Current protection counts by field
        current_protecting_by_field = {fld.id: [] for fld in threatened_fields}
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                tid = c.target_id
                for fld in threatened_fields:
                    if fld.id == tid:
                        current_protecting_by_field[tid].append(c)
                        break

        # Helper: distance from drone to field center
        def distance_to_field(drone, f):
            cx, cy = field_center(f)
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return (dx*dx + dy*dy) ** 0.5

        # Plan: allocate to fields in threat order until we reach ceil(N/2) protection or exhaust
        target_protected_count = (total_drones + 1) // 2  # ceil(N/2)
        drones_assigned_to_field = {}  # field_id -> list of drones assigned in this step

        # First pass: ensure each field reaches its drones_for_full_protection if possible,
        # using the closest drones not already protecting that field.
        for f in threatened_fields:
            field_id = f.id
            max_for_field = int(getattr(f, "drones_for_full_protection", 0))
            current = len(current_protecting_by_field.get(field_id, []))
            if current >= max_for_field:
                # Already fully protected; keep as is
                for d in current_protecting_by_field.get(field_id, []):
                    environment.assign_group(d, f"protecting {field_id}")
                    self._last_protected_by_drone[id(d)] = field_id
                drones_assigned_to_field[field_id] = list(current_protecting_by_field.get(field_id, []))
                continue

            need = max_for_field - current
            if need <= 0:
                continue

            # Build candidate pool: drones not currently protecting this field
            candidates = [c for c in components if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id)]
            if not candidates:
                continue

            cx, cy = field_center(f)

            def score(drone):
                dx = getattr(drone.location, "x", 0.0) - cx
                dy = getattr(drone.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                # Prefer drones that previously protected this field (persistence)
                last = self._last_protected_by_drone.get(id(drone))
                last_match = 1 if last == field_id else 0
                # Sort by distance then by persistence (higher last_match first)
                return (dist, -last_match)

            candidates.sort(key=score)
            chosen = candidates[:need]

            assigned = []
            for d in chosen:
                environment.assign_group(d, f"protecting {field_id}")
                self._last_protected_by_drone[id(d)] = field_id
                assigned.append(d)

            drones_assigned_to_field[field_id] = current_protecting_by_field.get(field_id, []) + assigned

        # Second pass (if needed): try to push protection to additional fields to meet target_protected_count
        # Recalculate how many drones are currently protecting something (we consider the intentional protections)
        currently_protecting = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None]
        total_protected = len(currently_protecting)

        if total_protected < target_protected_count:
            # Fill other fields in threat order
            for f in threatened_fields:
                field_id = f.id
                max_for_field = int(getattr(f, "drones_for_full_protection", 0))
                current = len([c for c in currently_protecting if getattr(c, "target_id", None) == field_id])
                if current >= max_for_field:
                    continue
                need = max_for_field - current
                if need <= 0:
                    continue

                candidates = [c for c in components if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id)]
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
                    environment.assign_group(d, f"protecting {field_id}")
                    self._last_protected_by_drone[id(d)] = field_id
                    currently_protecting.append(d)

        # Finally, any drones not assigned to protecting a field go idle
        for c in components:
            # Determine if this drone is currently assigned to protecting any field in this step
            assigned = False
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                # It is protecting something; keep it as is
                assigned = True
            if not assigned:
                # Not currently protecting; ensure it's idle unless we explicitly assigned it above
                environment.assign_group(c, "idle")
                self._last_protected_by_drone[id(c)] = None