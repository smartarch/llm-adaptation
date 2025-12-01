from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If there are no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper to compute squared distance from drone to field center
        def field_center(field):
            cx = (field.left + field.right) * 0.5
            cy = (field.top + field.bottom) * 0.5
            return cx, cy

        def dist2_to_field_center(drone, field):
            cx, cy = field_center(field)
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return dx * dx + dy * dy

        # Sort threatened fields by threat level (desc)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Mapping to track which drones we've assigned in this step
        assigned_in_step = set()

        # TOP FIELD PROTECTION
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        target_top = getattr(top_field, "drones_for_full_protection", 0)

        # Current protectors of top_field
        current_top_protectors = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id]

        # If there are more protectors than needed, move extras to idle (prefer farthest)
        if len(current_top_protectors) > target_top:
            # Sort current protectors by distance to top_field center (descending)
            current_top_protectors.sort(key=lambda d: dist2_to_field_center(d, top_field), reverse=True)
            extras = current_top_protectors[: len(current_top_protectors) - target_top]
            for d in extras:
                environment.assign_group(d, "idle")
                assigned_in_step.add(d)
            current_top_protectors = current_top_protectors[len(current_top_protectors) - target_top:]

        # If we need more drones for top field, pick closest available drones
        need_top = max(0, target_top - len(current_top_protectors))
        if need_top > 0:
            # Drones not already protecting top_field
            candidates = []
            for d in components:
                if d in assigned_in_step:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    # already counted in current_top_protectors
                    continue
                candidates.append(d)
            # Sort by distance to top field center (ascending)
            candidates.sort(key=lambda d: dist2_to_field_center(d, top_field))
            for d in candidates[:need_top]:
                environment.assign_group(d, top_group)
                assigned_in_step.add(d)
                current_top_protectors.append(d)

        # After ensuring top field, assign protection to other threatened fields (if any)
        # Process remaining fields in threat order
        for f in threatened_fields[1:]:
            group_id = f"protecting {f.id}"
            target = getattr(f, "drones_for_full_protection", 0)

            # Current protectors of this field
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]

            # If over-protected, move extras to idle (prefer farthest)
            if len(current) > target:
                # determine farthest ones
                current.sort(key=lambda d: dist2_to_field_center(d, f), reverse=True)
                extras = current[: len(current) - target]
                for d in extras:
                    environment.assign_group(d, "idle")
                    assigned_in_step.add(d)
                current = current[len(current) - target:]

            # Need more drones for this field
            need = max(0, target - len(current))
            if need > 0:
                # Build pool of candidates not yet assigned to top_field or previously assigned
                pool = []
                for d in components:
                    if d in assigned_in_step:
                        continue
                    pool.append(d)
                # Sort by distance to this field center (ascending)
                pool.sort(key=lambda d: dist2_to_field_center(d, f))
                for d in pool[:need]:
                    environment.assign_group(d, group_id)
                    assigned_in_step.add(d)

        # Finally, assign any remaining unassigned drones to idle
        for d in components:
            if d not in assigned_in_step:
                environment.assign_group(d, "idle")