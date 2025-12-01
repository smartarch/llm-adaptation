Reasoning and strategy

- Requirement: always fully protect the single field with the highest threat_level (>0) using the closest drones, keeping any drones already protecting it. Remaining drones should not be needlessly reassigned, because churn (travel time) can increase damage.
- Approach:
  1. Identify fields with threat_level > 0. If none, send all drones to "idle".
  2. Choose the top field by threat_level.
  3. Keep drones already protecting or moving to that top field.
  4. Compute how many additional drones are needed for full protection. Recruit extra drones in this priority order: idle drones (closest first), drones moving to other fields (closest), then drones currently protecting other fields (closest). Using distance to the nearest point on the target field rectangle is a better proxy for travel time than center distance.
  5. Assign selected drones to "protecting {field.id}" for the top field. For all other drones, preserve their current protecting/moving assignment only if their target field still has threat_level > 0; otherwise assign them to "idle".
- This minimizes unnecessary reassignments while satisfying the must-protect-top-field rule.

```py
from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Protect the highest-threat field with the closest drones, preferring idle drones first to avoid
        disrupting ongoing protections. Keep drones already protecting fully-protected fields.
        Preserve existing assignments for drones targeting threatened fields unless they are needed for the top field.
        """
        # Helpers
        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        def distance_to_field_rect(drone, field):
            x = getattr(drone.location, "x", 0)
            y = getattr(drone.location, "y", 0)
            left = getattr(field, "left", 0)
            right = getattr(field, "right", 0)
            top = getattr(field, "top", 0)
            bottom = getattr(field, "bottom", 0)
            nx = clamp(x, left, right)
            ny = clamp(y, top, bottom)
            return hypot(x - nx, y - ny)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else idle_group

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: idle everyone
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Select top field by threat_level (highest)
        top_field = max(threatened_fields, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If protecting group missing, fallback all to idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        required = int(getattr(top_field, "drones_for_full_protection", 0))

        comps = list(components)

        # Drones already protecting or moving to the top field
        protecting_top = [c for c in comps if getattr(c, "state", None) == "protecting"
                          and getattr(c, "target_id", None) == top_field.id]
        moving_to_top = [c for c in comps if getattr(c, "state", None) == "moving_to_field"
                         and getattr(c, "target_id", None) == top_field.id and c not in protecting_top]

        assigned_to_top = set(protecting_top + moving_to_top)
        current_count = len(assigned_to_top)
        need = max(0, required - current_count)

        # Build candidate list excluding those already assigned to top
        candidates = []
        for c in comps:
            if c in assigned_to_top:
                continue
            state = getattr(c, "state", None)
            # Priority: idle=0, moving_to_field=1, protecting=2
            if state == "idle":
                pr = 0
            elif state == "moving_to_field":
                pr = 1
            else:
                pr = 2
            dist = distance_to_field_rect(c, top_field)
            candidates.append((pr, dist, c))

        # Sort by priority then distance
        candidates.sort(key=lambda x: (x[0], x[1]))

        # Select required number of additional drones (best-first)
        selected_for_top = []
        if need > 0:
            for pr, dist, c in candidates:
                selected_for_top.append(c)
                if len(selected_for_top) >= need:
                    break

        final_protect_top = set(protecting_top + moving_to_top + selected_for_top)

        # Build set of threatened ids for preserving other assignments
        threatened_ids = {f.id for f in threatened_fields}

        # Helper to get protecting group for a field id (falls back to idle if missing)
        def protecting_group_for(field_id):
            g = f"protecting {field_id}"
            return g if g in group_ids else None

        # Assign groups for all drones
        for c in comps:
            if c in final_protect_top:
                environment.assign_group(c, top_group)
                continue

            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)

            # Preserve protecting/moving to threatened fields
            if target in threatened_ids:
                grp = protecting_group_for(target)
                if grp:
                    environment.assign_group(c, grp)
                    continue

            # Otherwise idle
            environment.assign_group(c, idle_group)