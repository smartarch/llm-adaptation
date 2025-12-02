"""
SmartFarmAdaptation

Reasoning and strategy (high-level):
- The farm has multiple fields with varying threat_level (0..1). Each field also specifies
  how many drones are required for full protection (drones_for_full_protection).
- Drones can be in states like "idle", "moving_to_field", or "protecting" and have a
  target_id (field id) or None.

Objective (per instructions):
- Always fully protect the field with the highest threat level (among fields with threat_level > 0),
  by assigning the closest drones to that field until the required number (drones_for_full_protection)
  are assigned. If drones are already heading to or protecting that field, count them as already
  contributing and keep them assigned to the same protecting group.
- If the highest-threat field is already fully (or over-) protected, keep the drones there.
- Remaining drones may remain idle or continue protecting their current fields (if those fields
  still have threat>0). Every drone must be explicitly assigned to one of the allowed groups each step.

Detailed adaptation strategy:
1. Gather all fields with threat_level > 0 and form their protecting group names ("protecting {field.id}").
2. If there are no threatened fields, assign all drones to "idle".
3. Otherwise, choose the single field with the highest threat_level (tie-broken by field.id).
4. Count how many drones are already committed to that field: any drone whose target_id equals
   that field's id (this includes drones already protecting and those moving toward it).
   These drones will be explicitly assigned to "protecting {field.id}" (so they continue their action).
5. Determine how many additional drones are required to reach drones_for_full_protection.
6. From the other drones (those not already committed to the highest-threat field),
   pick the closest ones (by Euclidean distance to the field center) up to the remaining needed amount.
   Assign those selected drones to the highest-threat protecting group.
   (This may reassign drones that were previously protecting other, lower-threat fields.)
7. For any other drone that is not moved to the highest-threat field but currently has a target
   corresponding to another threatened field, keep it assigned to that field's protecting group.
8. All remaining drones are assigned to "idle".
9. Ensure we only use group_ids supplied by the environment. Do not attempt to assign to groups that do not exist.

Notes:
- The strategy attempts to minimize immediate damage by guaranteeing the single-most-threatened field
  is fully shielded using the closest available drones. It preserves existing commitments toward that field
  and otherwise prefers to leave other protecting drones in place unless they are needed to secure the top field.
- All assignments are explicitly made each step via environment.assign_group(component, group_id).
"""

from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List[object], environment: object, group_ids: List[str], step: int):
        # Helper: compute field center coordinates
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Build list of fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Prepare mapping of valid protecting group names for threatened fields
        protecting_group_for_field = {}
        for f in threatened_fields:
            gname = f"protecting {f.id}"
            if gname in group_ids:
                protecting_group_for_field[f.id] = gname
            # If the expected group is not present in group_ids, we won't assign to it.

        # If no threatened fields exist or no protecting groups, put all drones idle
        if not protecting_group_for_field:
            for c in components:
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
                else:
                    # Fallback: assign first available group if "idle" is absent (unlikely)
                    environment.assign_group(c, group_ids[0] if group_ids else "idle")
            return

        # Choose highest-threat field (tie-break by id for determinism)
        def field_key(f):
            return (f.threat_level, f.id)
        highest_field = max(threatened_fields, key=field_key)
        highest_group = protecting_group_for_field.get(highest_field.id, None)

        # Compute center once
        hf_cx, hf_cy = field_center(highest_field)

        # Identify drones already committed to the highest field (target_id == highest_field.id)
        # These drones will remain assigned to that protecting group.
        committed_to_highest_ids = set()
        for c in components:
            try:
                if c.target_id == highest_field.id:
                    committed_to_highest_ids.add(id(c))
            except Exception:
                # In case a component has no target_id attribute or similar
                pass

        # How many drones are required for full protection
        required = getattr(highest_field, "drones_for_full_protection", 0)
        current_committed = len(committed_to_highest_ids)
        needed_remaining = max(0, int(required) - current_committed)

        # Select closest drones (by Euclidean distance) among those not already committed to highest
        # Build list of candidate drones (component, distance)
        candidates = []
        for c in components:
            if id(c) in committed_to_highest_ids:
                continue
            # compute distance to highest field center
            try:
                dx = float(c.location.x) - hf_cx
                dy = float(c.location.y) - hf_cy
                dist2 = dx * dx + dy * dy
            except Exception:
                # If location missing, put them at large distance so they are least preferred
                dist2 = float("inf")
            candidates.append((dist2, c))

        # Sort by distance, choose up to needed_remaining
        candidates.sort(key=lambda x: x[0])
        selected_for_highest_ids = set()
        for i in range(min(needed_remaining, len(candidates))):
            _, comp = candidates[i]
            selected_for_highest_ids.add(id(comp))

        # Now perform final assignment for each component exactly once
        for c in components:
            cid = id(c)
            assigned_group = None

            # If this drone is either committed to highest or was selected to move there, assign to highest group
            if highest_group is not None and (cid in committed_to_highest_ids or cid in selected_for_highest_ids):
                assigned_group = highest_group
            else:
                # If drone's current target is a threatened field and that protecting group exists, keep it there
                target = getattr(c, "target_id", None)
                if target in protecting_group_for_field:
                    assigned_group = protecting_group_for_field[target]
                else:
                    # Otherwise idle
                    if "idle" in group_ids:
                        assigned_group = "idle"
                    else:
                        # fallback to any valid group (shouldn't be needed)
                        assigned_group = group_ids[0] if group_ids else "idle"

            # Finally, assign via environment
            environment.assign_group(c, assigned_group)