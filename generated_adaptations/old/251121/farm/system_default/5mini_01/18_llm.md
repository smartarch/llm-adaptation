Reasoning and strategy

Goal: minimize damage by making the single highest-threat field reach full protection as quickly as possible while avoiding unnecessary disruption of protections already in place on other fields.

Key ideas
- Always fully protect the highest-threat field (tie-break by id) using the required number of drones.
- Prefer drones that are not currently "protecting" other fields (i.e., idle or moving) to avoid breaking existing protections. Among those, choose the closest drones (distance to the field rectangle).
- Include drones already protecting or moving to the top field first (they are effectively committed).
- Only if there are not enough non-protecting drones available do we pull drones that are protecting other fields; when pulling, choose protectors from the lowest-threat fields first and among those choose the closest drones to minimize collateral damage.
- All drones must be assigned explicitly each step. Drones not assigned to protect the top field are returned to protecting their original field (if they were protecting) or set to idle.
- Use distance to the field rectangle (not center) and drone speed 2 when considering closeness.

This keeps protections stable where possible and gets the top-priority field protected quickly with minimal collateral harm.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Strategy:
    - Fully protect the highest-threat field using the required number of drones.
    - Prefer drones that are not currently protecting other fields (idle or moving), choosing the closest ones.
    - Keep drones already protecting the top field.
    - Only pull protecting drones from other fields if necessary; pull from lowest-threat fields first,
      choosing the closest protectors to the top field.
    - All other drones remain protecting their field (if they were protecting) or become idle.
    """

    DRONE_SPEED = 2.0  # units per time (informational, not directly used except for reasoning)

    def assign_drones(self, components, environment, group_ids, step: int):
        def dist_to_rect(drone, field):
            x = getattr(drone.location, "x", 0.0)
            y = getattr(drone.location, "y", 0.0)
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            dx = 0.0
            dy = 0.0
            if x < left:
                dx = left - x
            elif x > right:
                dx = x - right
            if y < top:
                dy = top - y
            elif y > bottom:
                dy = y - bottom
            return math.hypot(dx, dy)

        idle_group = "idle"

        # Collect threatened fields
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all to idle
        if not fields:
            for comp in components:
                environment.assign_group(comp, idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group))
            return

        # Choose the field with the highest threat (tie-break by id string)
        top_field = max(fields, key=lambda f: (f.threat_level, str(getattr(f, "id", ""))))
        top_group = f"protecting {top_field.id}"
        required = int(getattr(top_field, "drones_for_full_protection", 0))

        # Map protecting drones by field, and collect other drones
        protecting_by_field = {f.id: [] for f in fields}
        moving_to_field = {f.id: [] for f in fields}
        idle_drones = []
        other_drones = []  # e.g., moving to non-threat or unknown

        for comp in components:
            state = getattr(comp, "state", None)
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target in protecting_by_field:
                protecting_by_field[target].append(comp)
            elif state == "moving_to_field" and target in moving_to_field:
                moving_to_field[target].append(comp)
            elif state == "idle":
                idle_drones.append(comp)
            else:
                other_drones.append(comp)

        # Start selection for top field
        selected = []

        # 1) Keep those already protecting the top field
        for c in protecting_by_field.get(top_field.id, []):
            if c not in selected:
                selected.append(c)

        # 2) Include those already moving to the top field
        for c in moving_to_field.get(top_field.id, []):
            if c not in selected:
                selected.append(c)

        # 3) Fill from candidates that are NOT currently protecting other fields:
        # candidates = idle + other_drones + moving_to_field for other targets (they are not protecting)
        non_protecting_candidates = []
        # include idle and non-protecting movers/others
        non_protecting_candidates.extend(idle_drones)
        non_protecting_candidates.extend([c for c in other_drones if c not in non_protecting_candidates])
        # include moving_to_field for fields (but exclude those moving to a field they are protecting)
        for fid, movers in moving_to_field.items():
            if fid == top_field.id:
                continue
            non_protecting_candidates.extend(c for c in movers if c not in non_protecting_candidates)

        # Sort non-protecting candidates by distance to top field and take as many as needed
        need = max(0, required - len(selected))
        if need > 0:
            non_protecting_candidates_sorted = sorted(non_protecting_candidates, key=lambda c: dist_to_rect(c, top_field))
            for c in non_protecting_candidates_sorted:
                if need <= 0:
                    break
                if c not in selected:
                    selected.append(c)
                    need -= 1

        # 4) If still need drones, pull surplus protecting drones from other fields (those with more protectors than required)
        if len(selected) < required:
            need = required - len(selected)
            surplus_candidates = []
            for f in fields:
                if f.id == top_field.id:
                    continue
                current = protecting_by_field.get(f.id, [])
                req_f = int(getattr(f, "drones_for_full_protection", 0))
                surplus = max(0, len(current) - req_f)
                if surplus > 0:
                    # choose surplus protectors closest to top_field
                    sorted_current = sorted(current, key=lambda c: dist_to_rect(c, top_field))
                    for c in sorted_current[:surplus]:
                        surplus_candidates.append((f, c))
            # sort surplus candidates by distance to top_field (they are all less preferred than non-protecting)
            surplus_candidates.sort(key=lambda fc: dist_to_rect(fc[1], top_field))
            for f, c in surplus_candidates:
                if len(selected) >= required:
                    break
                if c not in selected:
                    selected.append(c)

        # 5) If still need drones, reluctantly pull protecting drones from other fields starting with lowest-threat fields
        if len(selected) < required:
            need = required - len(selected)
            protect_list = []
            for f in sorted(fields, key=lambda ff: (ff.threat_level, str(getattr(ff, "id", "")))):
                if f.id == top_field.id:
                    continue
                for c in protecting_by_field.get(f.id, []):
                    if c not in selected:
                        protect_list.append((f, c))
            for f, c in protect_list:
                if len(selected) >= required:
                    break
                selected.append(c)

        # Now selected contains up to required drones (or fewer if not enough drones available)
        # Build assignment map
        assignments = {}

        # Assign selected to top field protecting group
        for comp in selected:
            assignments[comp] = top_group if top_group in group_ids else (idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group))

        # Re-assign protecting drones that were not selected back to their protecting group
        for fid, comps in protecting_by_field.items():
            grp = f"protecting {fid}"
            for comp in comps:
                if comp in assignments:
                    continue
                # if this protector was not pulled, keep it protecting its field
                assignments[comp] = grp if grp in group_ids else (idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group))

        # Any remaining drones that are moving_to_field (but not protecting) and not selected: keep their existing target if it's the top field move else idle
        for fid, movers in moving_to_field.items():
            for comp in movers:
                if comp in assignments:
                    continue
                # If mover targets the top_field but wasn't selected (rare), still allow it to continue moving to its target
                if fid == top_field.id:
                    assignments[comp] = top_group if top_group in group_ids else (idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group))
                else:
                    # movers to other fields: set to idle to avoid partial protection
                    assignments[comp] = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # All other drones (idle_drones and other_drones) that are not assigned: set to idle
        for comp in components:
            if comp not in assignments:
                assignments[comp] = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Commit assignments
        for comp, grp in assignments.items():
            environment.assign_group(comp, grp)