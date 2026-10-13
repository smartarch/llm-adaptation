from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def _distance_sq(self, drone, field):
        """Squared distance from drone to the closest point on the field rectangle."""
        x, y = drone.location.x, drone.location.y
        min_x, max_x = min(field.left, field.right), max(field.left, field.right)
        min_y, max_y = min(field.top, field.bottom), max(field.top, field.bottom)

        cx = min(max(x, min_x), max_x)
        cy = min(max(y, min_y), max_y)

        dx = x - cx
        dy = y - cy
        return dx * dx + dy * dy

    def assign_drones(self, components, environment, group_ids, step: int):
        fields_by_id = {f.id: f for f in environment.fields}
        valid_groups = set(group_ids)
        idle_group = "idle" if "idle" in valid_groups else None

        def group_for_field(field):
            return f"protecting {field.id}"

        def current_field(drone):
            """Return the field id a drone is currently assigned to, if valid."""
            if drone.state in ("moving_to_field", "protecting") and drone.target_id is not None:
                field = fields_by_id.get(drone.target_id)
                if field is not None and field.threat_level > 0:
                    g = group_for_field(field)
                    if g in valid_groups:
                        return field.id
            return None

        # Only fields that are threatened, need protection, and have a valid group
        active_fields = []
        for field in environment.fields:
            if field.threat_level > 0 and field.drones_for_full_protection > 0:
                if group_for_field(field) in valid_groups:
                    active_fields.append(field)

        # Highest threat first
        active_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        unassigned = set(components)
        assignments = {}  # component -> group_id

        for field in active_fields:
            capacity = field.drones_for_full_protection
            target_group = group_for_field(field)

            # Keep already-assigned drones for this field, up to capacity.
            existing = [c for c in unassigned if current_field(c) == field.id]
            existing.sort(key=lambda c: (self._distance_sq(c, field), id(c)))
            keep = existing[:capacity]
            for c in keep:
                assignments[c] = target_group
                unassigned.remove(c)

            # Fill remaining slots with the closest available drones.
            needed = capacity - len(keep)
            if needed > 0:
                candidates = sorted(
                    unassigned,
                    key=lambda c: (self._distance_sq(c, field), id(c))
                )
                for c in candidates[:needed]:
                    assignments[c] = target_group
                    unassigned.remove(c)

        # Any remaining drones are idle.
        for c in list(unassigned):
            if idle_group is not None:
                assignments[c] = idle_group
            elif valid_groups:
                assignments[c] = next(iter(valid_groups))
            unassigned.remove(c)

        # Explicitly re-assign every component.
        for c in components:
            group_id = assignments.get(c)
            if group_id is not None:
                environment.assign_group(c, group_id)