

The bug is a simple typo on line 64: I wrote `env.assign_group(...)` instead of `environment.assign_group(...)`. Let me fix that.

```py
import math
import generated_adaptations.base_classes.farm as base


class SmartFarmAdaptation(base.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build set of valid protection group ids for quick lookup
        valid_protect_groups = {g for g in group_ids if g != "idle"}
        # Map field_id -> group name
        field_to_group = {}
        for g in valid_protect_groups:
            # group name format: "protecting <field_id>"
            field_id = g.replace("protecting ", "")
            field_to_group[field_id] = g

        # Build a dict of active fields (threat > 0) sorted by threat descending
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)
        active_field_ids = {f.id for f in active_fields}

        # Categorize drones
        # Committed drones: already protecting or moving_to a field that still needs protection
        committed = {}  # field_id -> list of drones
        available = []  # drones free to reassign

        for drone in components:
            if (
                drone.state in ("protecting", "moving_to_field")
                and drone.target_id is not None
                and drone.target_id in active_field_ids
                and field_to_group.get(drone.target_id) in valid_protect_groups
            ):
                # Keep this drone where it is (avoid unnecessary reassignment)
                committed.setdefault(drone.target_id, []).append(drone)
            else:
                available.append(drone)

        # For each field in priority order, top up to full protection
        for field in active_fields:
            required = field.drones_for_full_protection
            already = len(committed.get(field.id, []))
            needed = max(0, required - already)

            if needed > 0 and available:
                # Sort available drones by distance to this field, pick the closest
                available.sort(key=lambda d: self._dist_to_field(d, field))
                picked = available[:needed]
                committed.setdefault(field.id, []).extend(picked)
                available = available[needed:]

        # Now perform group assignments
        # Build a mapping: id(drone) -> field_id
        drone_assignment = {}
        for field_id, drones in committed.items():
            for d in drones:
                drone_assignment[id(d)] = field_id

        for drone in components:
            if id(drone) in drone_assignment:
                fid = drone_assignment[id(drone)]
                environment.assign_group(drone, field_to_group[fid])
            else:
                environment.assign_group(drone, "idle")

    @staticmethod
    def _dist_to_field(drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = drone.location.x - cx
        dy = drone.location.y - cy
        return math.sqrt(dx * dx + dy * dy)
```