Reasoning and strategy

Goal summary
- Always fully protect the single most threatened field using the closest drones, and do not overprotect it.
- Prefer to fully protect additional fields only if there are enough spare drones.
- Keep at least half of the fleet actively protecting fields when possible.
- Keep drone assignments stable: prefer to retain drones that are already protecting a field rather than reassigning them (so at least half the drones tend to remain on the same group over time).
- Avoid many partially protected fields because partial protection is not very effective; only allow partial protection to meet the "at least half protecting" requirement if there are not enough drones to fully protect additional fields.

How the strategy works (step-by-step)
1. Track the previous group assignment per drone (by object id) across adaptation steps to encourage stability.
2. Select the single most threatened field (highest threat_level among fields with threat>0). If none exist, assign all drones to "idle".
3. For that most threatened field:
   - Determine how many drones are required (field.drones_for_full_protection).
   - Choose drones in the following priority order until the required number is met:
     a) drones already protecting that field (stability),
     b) drones that are moving to that field (already targeting it),
     c) other drones sorted by proximity to the field center (closest first).
   - Assign exactly the required number; do not overprotect.
4. For other fields (sorted by descending threat), fully protect them only if we have enough remaining drones to meet their full requirement (using similar prioritization). This avoids many partial protections.
5. After attempting to fully protect additional fields, ensure at least half of the drones are used for protection. If not, assign remaining drones (closest-first) to the highest-threat remaining field(s) even if that results in partial protection — this is used only to meet the "at least half protecting" constraint.
6. All leftover drones are assigned to "idle".
7. Update the stored previous-group mapping so that future steps prefer to keep drones in their current groups.

Notes on stability and the “don’t change too often” requirement
- By preferring drones that are already protecting a field when filling protection slots, the algorithm minimizes churn.
- Also, when selecting drones to move away from a group, it naturally avoids moving drones that were already assigned there previously, because they will be at the top of the priority list for that group. This encourages a stable set of drones staying on the same fields across steps.

Now the Python implementation.

```py
from math import hypot
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track previous group per drone (keyed by id(component)) to encourage stability
        # Value is the group string like "idle" or "protecting {field.id}"
        self._previous_group = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance_to_field(self, drone, field):
        cx, cy = self._field_center(field)
        dx = getattr(drone.location, "x", 0) - cx
        dy = getattr(drone.location, "y", 0) - cy
        return hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # Map for quick field lookup by id
        field_by_id = {f.id: f for f in environment.fields}

        # Helper to form group name for a field
        def group_name_for(field_id):
            return f"protecting {field_id}"

        # Initialize prev groups for drones that are newly seen
        for drone in components:
            key = id(drone)
            if key not in self._previous_group:
                # Derive initial group from observable state
                if getattr(drone, "state", None) == "idle" or getattr(drone, "target_id", None) is None:
                    self._previous_group[key] = "idle"
                else:
                    # moving_to_field or protecting with a target
                    tgt = getattr(drone, "target_id", None)
                    if tgt is None:
                        self._previous_group[key] = "idle"
                    else:
                        self._previous_group[key] = group_name_for(tgt)

        # If no threatened fields, put everyone idle
        if not fields:
            for drone in components:
                grp = "idle" if "idle" in group_ids else group_ids[0]
                environment.assign_group(drone, grp)
                self._previous_group[id(drone)] = grp
            return

        # Choose the most threatened field (highest threat_level). Tie-breaking: higher drones_for_full_protection then arbitrary.
        primary_field = max(fields, key=lambda f: (f.threat_level, getattr(f, "drones_for_full_protection", 0)))
        primary_group = group_name_for(primary_field.id)

        total_drones = len(components)
        half_needed = (total_drones + 1) // 2  # at least half (ceil)

        # Prepare lists and metadata for drones
        drones_info = []
        for drone in components:
            key = id(drone)
            prev_grp = self._previous_group.get(key, "idle")
            # derive current observable group as well (state + target_id)
            if getattr(drone, "state", None) == "idle" or getattr(drone, "target_id", None) is None:
                obs_group = "idle"
            else:
                obs_group = group_name_for(getattr(drone, "target_id"))
            dist_to_primary = self._distance_to_field(drone, primary_field)
            drones_info.append({
                "drone": drone,
                "key": key,
                "prev_group": prev_grp,
                "obs_group": obs_group,
                "dist_to_primary": dist_to_primary
            })

        assigned = {}  # key -> group string

        # Function to select N drones for a given field (without overprotecting)
        def select_drones_for_field(field, n_needed, already_taken_keys=set()):
            # prioritization:
            # 1) drones already (previously) in that protecting group
            # 2) drones whose observable target/state is that field
            # 3) other drones sorted by distance to that field center
            field_grp = group_name_for(field.id)
            center_dist_cache = {}
            def dist_to_field_info(info):
                if info["key"] in already_taken_keys:
                    return float("inf")
                if info["key"] in assigned:
                    return float("inf")
                # compute distance to given field center
                if info["key"] not in center_dist_cache:
                    center_dist_cache[info["key"]] = self._distance_to_field(info["drone"], field)
                return center_dist_cache[info["key"]]

            candidates = []
            # collect candidates preserving priority
            for info in drones_info:
                k = info["key"]
                if k in already_taken_keys or k in assigned:
                    continue
                if info["prev_group"] == field_grp:
                    candidates.append((0, 0, info))  # highest priority
                elif info["obs_group"] == field_grp:
                    candidates.append((1, info["dist_to_primary"], info))  # next priority (distance to primary as tie)
                else:
                    # lower priority, use actual distance to this field for sorting
                    candidates.append((2, dist_to_field_info(info), info))
            # sort by priority and distance
            candidates.sort(key=lambda x: (x[0], x[1]))
            chosen = []
            for _, _, info in candidates:
                if len(chosen) >= n_needed:
                    break
                chosen.append(info)
            return chosen

        # 1) Assign required drones to primary field
        n_primary_required = int(getattr(primary_field, "drones_for_full_protection", 1))
        primary_selected_infos = select_drones_for_field(primary_field, n_primary_required)
        for info in primary_selected_infos:
            assigned[info["key"]] = primary_group

        # 2) Try to fully protect other fields using remaining drones
        # Sort remaining fields by threat desc, exclude primary
        other_fields = [f for f in fields if f.id != primary_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for field in other_fields:
            n_req = int(getattr(field, "drones_for_full_protection", 1))
            # count already assigned to that field (unlikely yet)
            already_for_field = sum(1 for k, g in assigned.items() if g == group_name_for(field.id))
            needed = max(0, n_req - already_for_field)
            available_keys = set(info["key"] for info in drones_info) - set(assigned.keys())
            if needed <= 0:
                continue
            # Only fully protect if we have enough drones left to fill requirement
            if len(available_keys) >= needed:
                selected_infos = select_drones_for_field(field, needed)
                if len(selected_infos) >= needed:
                    for info in selected_infos:
                        assigned[info["key"]] = group_name_for(field.id)
            # else skip to avoid partial protection

        # 3) Ensure at least half of drones are protecting something.
        currently_protecting = sum(1 for g in assigned.values() if g != "idle")
        # If not enough, allow partial protection for the highest-threat remaining fields
        if currently_protecting < half_needed:
            needed_more = half_needed - currently_protecting
            # Build list of candidate fields ordered by threat (including primary and others)
            fields_by_threat = sorted(fields, key=lambda f: f.threat_level, reverse=True)
            # We'll allow partial fill up to needed_more but not exceed a field's full requirement
            for field in fields_by_threat:
                if needed_more <= 0:
                    break
                field_grp = group_name_for(field.id)
                already_assigned_for_field = sum(1 for k, g in assigned.items() if g == field_grp)
                max_for_field = int(getattr(field, "drones_for_full_protection", 1))
                can_add = max_for_field - already_assigned_for_field
                if can_add <= 0:
                    continue
                to_add = min(can_add, needed_more)
                selected_infos = select_drones_for_field(field, to_add)
                for info in selected_infos:
                    assigned[info["key"]] = field_grp
                    needed_more -= 1
                    if needed_more <= 0:
                        break
            # If still not enough (no fields or exhausted), we can't do more; leftover drones remain idle

        # 4) Assign unassigned drones to idle
        for info in drones_info:
            k = info["key"]
            if k not in assigned:
                assigned[k] = "idle"

        # Ensure group names are valid (present in group_ids); otherwise fallback to "idle"
        valid_group_set = set(group_ids)
        for info in drones_info:
            drone = info["drone"]
            grp = assigned[info["key"]]
            if grp not in valid_group_set:
                # fallback to idle or first valid group
                fallback = "idle" if "idle" in valid_group_set else (group_ids[0] if group_ids else "idle")
                grp = fallback
            environment.assign_group(drone, grp)
            # update previous group tracking
            self._previous_group[info["key"]] = grp