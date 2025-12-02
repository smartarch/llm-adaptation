"""
Improved adaptation strategy:
- Fully protect as many threatened fields as possible, starting from the highest threat.
- For each field, use the closest available drones to fill any shortfall to full protection.
- Drones already protecting or en route to a threatened field contribute to that field's protection.
- Drones not needed for protection are assigned to "idle".
"""

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields (threat_level > 0)
        fields = getattr(environment, "fields", [])
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened_sorted = sorted(threatened, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Map field.id to its corresponding group name (if available)
        field_to_group = {}
        for f in threatened_sorted:
            g = f"protecting {f.id}"
            field_to_group[f.id] = g if g in group_ids else None

        assigned = set()

        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field_center(drone, field):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(field)
            dx = loc.x - cx
            dy = loc.y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Allocate drones to fields in priority order
        for field in threatened_sorted:
            group = field_to_group.get(field.id)
            if group is None:
                # No group for this field (unexpected), skip
                continue

            # Current protectors for this field (protecting or moving_to_field with this target)
            current = [
                d for d in components
                if getattr(d, "target_id", None) == field.id
                and getattr(d, "state", None) in ("protecting", "moving_to_field")
            ]
            current_set = set(current)
            current_count = len(current)

            drones_needed = getattr(field, "drones_for_full_protection", 0)

            # If already fully protected, ensure they are in the correct group
            if current_count >= drones_needed:
                for d in current:
                    environment.assign_group(d, group)
                    assigned.add(d)
                continue

            # Assign current protectors to the field's group
            for d in current:
                environment.assign_group(d, group)
                assigned.add(d)

            shortfall = max(0, drones_needed - current_count)

            if shortfall > 0:
                # Choose closest unassigned drones to fill the shortfall
                candidates = [d for d in components if d not in assigned]
                candidates.sort(key=lambda dr: distance_to_field_center(dr, field))
                for i in range(min(shortfall, len(candidates))):
                    d = candidates[i]
                    environment.assign_group(d, group)
                    assigned.add(d)

        # Any remaining drones are idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")