"""
Adaptive strategy (refined):
- Goal: reduce overall damage by more effectively utilizing drones across fields.
- Process fields in descending order of threat level to prioritize the most dangerous field(s).
- For each field:
  - Preserve any drones already protecting that field (to minimize churn) by assigning them to "protecting <field_id>".
  - Compute how many additional drones are needed to reach full protection (based on field.drones_for_full_protection).
  - Reassign the closest available drones (not yet allocated in this pass) to the field until either:
    a) the field is fully protected, or
    b) there are no drones left to allocate.
- After attempting to fully protect as many high-threat fields as possible, any remaining drones are set to idle.
- This approach minimizes movement for drones already protecting a high-threat field, reduces the number of drones left idle, and prioritizes coverage for the most threatening fields first.
- All drones end up in one of the groups: "idle" or "protecting {field_id}".
"""

import math
from generated_adaptations.base_classes import farm as base_farm

class SmartFarmAdaptation(base_farm.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no field is threatened, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low)
        fields_desc = sorted(fields_with_threat, key=lambda fld: getattr(fld, "threat_level", 0), reverse=True)

        # Helper: compute field center
        def field_center(field):
            left = getattr(field, "left", 0)
            right = getattr(field, "right", 0)
            top = getattr(field, "top", 0)
            bottom = getattr(field, "bottom", 0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        final_group = {}
        allocated = set()

        # Process fields in threat order
        for field in fields_desc:
            fid = getattr(field, "id", None)
            if fid is None:
                continue
            group = f"protecting {fid}"
            center = field_center(field)

            # Current protectors for this field
            current = [c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid]

            # Assign current protectors to this field
            for d in current:
                final_group[d] = group
                allocated.add(d)

            # Drones needed to fully protect this field
            required = int(getattr(field, "drones_for_full_protection", 0) or 0)
            need = max(0, required - len(current))

            if need > 0:
                # Build candidate pool of drones not yet allocated
                candidates = [c for c in components if c not in allocated]
                cand_with_dist = []
                for c in candidates:
                    loc = getattr(c, "location", None)
                    if loc is None or not hasattr(loc, "x") or not hasattr(loc, "y"):
                        dist = float("inf")
                    else:
                        dist = math.hypot(loc.x - center[0], loc.y - center[1])
                    cand_with_dist.append((dist, c))
                cand_with_dist.sort(key=lambda t: t[0])

                # Assign as many as needed (or as many as available)
                to_assign = min(need, len(cand_with_dist))
                for i in range(to_assign):
                    c = cand_with_dist[i][1]
                    final_group[c] = group
                    allocated.add(c)

        # Any drones not allocated to a protecting group become idle
        for c in components:
            if c not in allocated:
                final_group[c] = "idle"

        # Apply assignments
        for c in components:
            environment.assign_group(c, final_group.get(c, "idle"))