from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper to compute field center
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

        # Current protectors per field
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
            # Sort by distance to top field center (farthest first)
            current_top.sort(key=lambda d: dist2_to_field_center(d, top_field), reverse=True)
            extras = current_top[: len(current_top) - max(target_top, 0)]
            for d in extras:
                environment.assign_group(d, "idle")
                assigned.add(d)
            current_top = current_top[len(current_top) - max(target_top, 0):]

        # If need more for top field, allocate closest drones
        need_top = max(0, max(target_top, 0) - len(current_top))
        if need_top > 0:
            # Candidates are drones not yet assigned
            candidates = []
            for d in components:
                if d in assigned:
                    continue
                # If already protecting top field, skip (already counted)
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                candidates.append(d)
            candidates.sort(key=lambda d: dist2_to_field_center(d, top_field))
            for d in candidates[:need_top]:
                environment.assign_group(d, top_group)
                assigned.add(d)
                current_top.append(d)

        # Assign remaining fields in threat order
        for f in threatened_fields[1:]:
            target = getattr(f, "drones_for_full_protection", 0)
            group_id = f"protecting {f.id}"
            current = current_protectors_by_field.get(f.id, [])
            # If over-protected, move extras (farthest) to idle
            if len(current) > max(target, 0):
                current.sort(key=lambda d: dist2_to_field_center(d, f), reverse=True)
                extras = current[: len(current) - max(target, 0)]
                for d in extras:
                    environment.assign_group(d, "idle")
                    assigned.add(d)
                current = current[len(current) - max(target, 0):]

            need = max(0, max(target, 0) - len(current))
            if need > 0:
                # Pool of available drones not yet assigned
                pool = []
                for d in components:
                    if d in assigned:
                        continue
                    pool.append(d)
                pool.sort(key=lambda d: dist2_to_field_center(d, f))
                for d in pool[:need]:
                    environment.assign_group(d, group_id)
                    assigned.add(d)

        # Finally, any unassigned drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")