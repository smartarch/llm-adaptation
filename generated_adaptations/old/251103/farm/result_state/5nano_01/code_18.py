"""
Strategy rationale:
- In each tick, consider every field with threat_level > 0.
- For each field, compute:
  - current_protecting: drones currently assigned to protect or on the way to this field
  - inbound: arriving_drones (count towards protection)
  - deficit: how many more drones are needed to reach drones_for_full_protection
- Prioritize fields by (threat_level, deficit) so the highest-threat fields that are most in need get protected first.
- For each field in that priority order, allocate the closest available drones to fill its deficit, without evicting drones that are already protecting a higher-priority field.
- Drones already protecting or arriving to a field are kept in that field's group (if possible); newly allocated drones are assigned to the same field's protecting group.
- Remaining drones are set to idle.

This approach aggressively and safely distributes drones to maximize protection of the most dangerous fields while respecting the requirement to re-assign every drone to one group each step.
"""

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 0) Gather fields with positive threat levels
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper: compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # 1) Build per-field view: current_protecting, inbound, required, deficit
        field_entries = []
        for f in fields:
            # Current drones targeting this field (protecting or en route)
            current_for_field = []
            for idx, d in enumerate(components):
                if getattr(d, "target_id", None) == f.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                    current_for_field.append(idx)

            current_count = len(current_for_field)
            inbound = getattr(f, "arriving_drones", 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            deficit = max(0, required - (current_count + inbound))

            field_entries.append({
                "field": f,
                "group": f"protecting {f.id}",
                "deficit": deficit,
                "current_for_field": current_for_field,
                "inbound": inbound,
                "required": required,
            })

        # If nothing has a deficit, idle all (or keep as is by re-assigning to their groups below)
        if not field_entries:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by priority: highest threat first, then largest deficit
        field_entries.sort(key=lambda e: (-e["field"].threat_level, -e["deficit"]))

        assigned_indices = set()

        # 3) Allocate drones to fields in priority order
        for info in field_entries:
            f = info["field"]
            g_name = info["group"]
            if g_name not in group_ids:
                continue

            # Ensure current drones are in the correct group
            for idx in info["current_for_field"]:
                environment.assign_group(components[idx], g_name)
            assigned_indices.update(info["current_for_field"])

            deficit = info["deficit"]
            if deficit <= 0:
                continue

            # Pick closest available drones to fill the deficit
            cx, cy = center_of(f)
            candidates = []
            for idx, d in enumerate(components):
                if idx in assigned_indices:
                    continue
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, idx))
            candidates.sort()

            for i in range(min(deficit, len(candidates))):
                idx = candidates[i][1]
                environment.assign_group(components[idx], g_name)
                assigned_indices.add(idx)

        # 4) Remaining drones go idle
        for idx, d in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(d, "idle")