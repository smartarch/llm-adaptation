import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Get all fields that currently have a threat level > 0
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        # Sort by threat level descending (highest threat first), then by id for determinism
        threatened_fields.sort(key=lambda f: (-f.threat_level, f.id))

        field_by_id = {f.id: f for f in threatened_fields}

        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def distance(drone, field):
            cx, cy = field_center(field)
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return math.hypot(dx, dy)

        # Determine the current target field for each drone, if it is still valid
        current_field = {}
        for c in components:
            if c.state in ("moving_to_field", "protecting") and c.target_id in field_by_id:
                current_field[c] = c.target_id
            else:
                current_field[c] = None

        assigned = set()
        assignment = {}

        # Process fields in order of decreasing threat
        for field in threatened_fields:
            required = field.drones_for_full_protection
            if required <= 0:
                continue

            # Drones that are already committed to this field and not yet assigned to a higher-threat field
            current_drones = [
                c for c in components
                if current_field.get(c) == field.id and c not in assigned
            ]
            # Prefer drones that are already protecting, then those closest to the field
            current_drones.sort(key=lambda c: (0 if c.state == "protecting" else 1, distance(c, field)))

            # Keep up to the required number of already-committed drones
            keep = current_drones[:required]
            for c in keep:
                assignment[c] = f"protecting {field.id}"
                assigned.add(c)

            if len(keep) >= required:
                continue

            # Need additional drones: pick the closest available ones from all unassigned drones
            needed = required - len(keep)
            candidates = [c for c in components if c not in assigned]
            candidates.sort(key=lambda c: distance(c, field))

            for c in candidates[:needed]:
                assignment[c] = f"protecting {field.id}"
                assigned.add(c)

        # Any drone not assigned to a field becomes idle
        for c in components:
            if c not in assignment:
                assignment[c] = "idle"

        # Apply the assignments
        for c, gid in assignment.items():
            if gid in group_ids:
                environment.assign_group(c, gid)
            else:
                # Safeguard: if the intended group is not valid, fall back to idle
                environment.assign_group(c, "idle")