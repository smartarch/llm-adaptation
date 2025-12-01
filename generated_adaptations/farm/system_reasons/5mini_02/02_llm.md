Reasoning and adaptation strategy

Goal summary
- Always fully protect the single most threatened field (highest threat_level) using as many drones as required by field.drones_for_full_protection.
- Use the closest drones to protect that field, but prefer to keep drones that are already assigned (moving_to_field or protecting) to the same target to avoid excessive churn.
- Avoid overprotection: never assign more drones to a field than drones_for_full_protection.
- Use remaining drones to fully protect other fields when possible (prioritizing higher-threat fields), again preferring drones already targeting those fields and using the closest available drones.
- Ensure at least half of the drones are assigned to protection. If after fully protecting fields there are fewer than half assigned, allocate additional closest idle/unassigned drones to the highest-threat remaining field (even if that does not reach full protection) until the "half" threshold is met.
- Any drone not assigned to a protecting group is assigned to the "idle" group.
- Always call environment.assign_group for every drone (even if the drone remains in the same group). Use only group names that exist in group_ids.

Stability & switching
- To reduce switching, selection sorts drones so those already targeting a given field are chosen first; then among the rest we choose by distance.
- This approach tends to keep at least half of the drones on the same field over time (because we prefer to keep existing protectors) while still meeting threat-driven reassignment goals.

Implementation outline
1. Collect fields with threat_level > 0. If none, assign all drones to "idle".
2. Identify the most threatened field (max threat_level).
3. Compute distances from each drone to each field center for selection.
4. Select the required number of drones for the most threatened field:
   - Sort drones by (already targeting that field? first) then by distance.
   - Pick top drones up to drones_for_full_protection.
5. For other fields (descending threat), try to fully protect them if enough spare drones exist, using the same selection logic for each field.
6. If after full-protection steps fewer than half the drones are protecting, assign additional closest unassigned drones to the highest-threat remaining field until at least half are protecting (partial protection allowed only to satisfy the "half used" requirement).
7. Assign every remaining drone to "idle".
8. Call environment.assign_group(component, group_id) for each component.

Code follows.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
import math as _math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy to allocate drones to fields on a smart farm.

    Key behaviors:
    - Fully protect the single most threatened field using the closest drones,
      preferring drones already targeting that field.
    - Avoid overprotection: never allocate more than drones_for_full_protection.
    - Try to fully protect additional fields (by threat priority) if enough drones remain.
    - Ensure at least half of the drones are used to protect fields; if not possible by full-
      protection of additional fields, allocate extra closest drones to the next-highest-threat
      field (partial protection) to meet the half-drones threshold.
    - Keep assignments stable by preferring drones that are already assigned/moving to the same field.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between a drone and a field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_field(component, field_center_xy):
            dx = component.location.x - field_center_xy[0]
            dy = component.location.y - field_center_xy[1]
            return math.hypot(dx, dy)

        # Validate presence of 'idle' group
        if "idle" not in group_ids:
            # If idle group is missing, fall back to first available group to avoid crashes.
            idle_group = group_ids[0] if group_ids else "idle"
        else:
            idle_group = "idle"

        # Collect threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        total_drones = len(components)
        # Minimal number of drones that we aim to have protecting fields (at least half)
        min_protectors = (total_drones + 1) // 2  # ceil(total/2)

        # If no threatened fields, assign all to idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Prepare a mapping of field_id -> field object for convenience
        field_by_id = {f.id: f for f in threatened_fields}

        # Choose the primary field (highest threat_level). Tie-breaker: larger drones_for_full_protection
        threatened_fields.sort(key=lambda f: (f.threat_level, getattr(f, "drones_for_full_protection", 0)), reverse=True)
        primary_field = threatened_fields[0]

        # Precompute field centers
        centers = {f.id: field_center(f) for f in threatened_fields}

        # Build helper lists for drones: for sorting and selection
        # We'll refer to drones by object identity; create a list of available drones
        all_drones = list(components)

        # Track assignment mapping: component -> group_name
        assignments = {}

        # Utility to select N drones for a given field:
        # Prefer drones already targeting that field (target_id == field.id),
        # then by distance to field center.
        def select_drones_for_field(field, candidates, N):
            if N <= 0:
                return []
            center = centers[field.id]
            scored = []
            for c in candidates:
                is_current = (getattr(c, "target_id", None) == field.id)
                d = dist_to_field(c, center)
                # Sort key: current targets first (False < True), then distance
                scored.append((not is_current, d, c))
            scored.sort(key=lambda x: (x[0], x[1]))
            return [t[2] for t in scored[:N]]

        # Start with all drones unassigned
        unassigned = set(all_drones)

        # 1) Assign primary field with required drones (closest, preferring current)
        req_primary = getattr(primary_field, "drones_for_full_protection", 0)
        # Select candidates from all drones
        primary_selected = select_drones_for_field(primary_field, unassigned, req_primary)
        for c in primary_selected:
            group_name = f"protecting {primary_field.id}"
            # Ensure group_name exists
            if group_name not in group_ids:
                # fallback to idle if group missing
                group_name = idle_group
            assignments[c] = group_name
            if c in unassigned:
                unassigned.remove(c)

        # 2) Try to fully protect other fields (by descending threat), reserving no overprotection
        for field in threatened_fields[1:]:
            req = getattr(field, "drones_for_full_protection", 0)
            if req <= 0:
                continue
            if len(unassigned) < req:
                continue  # not enough spare drones to fully protect this field
            # Prefer drones already targeting this field among unassigned
            selected = select_drones_for_field(field, unassigned, req)
            if len(selected) < req:
                continue
            for c in selected:
                group_name = f"protecting {field.id}"
                if group_name not in group_ids:
                    group_name = idle_group
                assignments[c] = group_name
                if c in unassigned:
                    unassigned.remove(c)

        # 3) Ensure at least half the drones are protecting; if not, allocate extra closest unassigned drones
        current_protecting_count = sum(1 for c in assignments if assignments[c].startswith("protecting "))
        if current_protecting_count < min_protectors:
            needed = min_protectors - current_protecting_count
            # Find the highest-threat field that is valid (first in threatened_fields)
            # Prefer fields already being protected; otherwise use the next-highest threat.
            # We'll pick a target_field_for_extra where group exists.
            # First attempt: reuse primary_field if group exists
            extra_target = None
            for f in threatened_fields:
                grp = f"protecting {f.id}"
                if grp in group_ids:
                    extra_target = f
                    break
            # If somehow none have group ids, we will make them idle (shouldn't happen)
            if extra_target is not None and unassigned:
                # Select closest unassigned drones to this extra_target
                extra_selected = select_drones_for_field(extra_target, unassigned, needed)
                for c in extra_selected:
                    group_name = f"protecting {extra_target.id}"
                    if group_name not in group_ids:
                        group_name = idle_group
                    assignments[c] = group_name
                    if c in unassigned:
                        unassigned.remove(c)
                # update count
                current_protecting_count = sum(1 for c in assignments if assignments[c].startswith("protecting "))

        # 4) Any drones still unassigned: assign them either to their current field (if that field is actively protected and not overprotected),
        #    or to idle. To reduce churn, if a drone is currently targeting a field that we have assigned protectors to
        #    and that group hasn't reached its capacity, keep it there.
        # Build counts per protecting group to enforce not overprotecting
        protect_counts = {}
        protect_caps = {}
        for f in threatened_fields:
            grp = f"protecting " + f.id
            cap = getattr(f, "drones_for_full_protection", 0)
            protect_caps[grp] = cap
            protect_counts[grp] = 0
        for c, g in assignments.items():
            if g.startswith("protecting "):
                protect_counts[g] = protect_counts.get(g, 0) + 1

        # Try to keep unassigned drones on their current target if that group's cap not reached
        for c in list(unassigned):
            current_target = getattr(c, "target_id", None)
            if current_target is not None:
                grp = f"protecting {current_target}"
                if grp in group_ids:
                    cap = protect_caps.get(grp, 0)
                    cur = protect_counts.get(grp, 0)
                    if cur < cap:
                        assignments[c] = grp
                        protect_counts[grp] = cur + 1
                        unassigned.remove(c)

        # Remaining unassigned: send to idle
        for c in list(unassigned):
            assignments[c] = idle_group
            unassigned.remove(c)

        # Final pass: make sure no field is overprotected (trim extras by selecting which drones to keep)
        # For each protecting group, if count > cap, we will keep drones that were already targeting that field if possible,
        # otherwise keep by proximity.
        for f in threatened_fields:
            grp = f"protecting " + f.id
            if grp not in group_ids:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            # collect drones currently assigned to this group
            assigned_drones = [c for c, g in assignments.items() if g == grp]
            if len(assigned_drones) <= cap:
                continue
            # prefer drones that had target_id==f.id
            def keep_key(c):
                # Keep drones already targeting this field first, then by distance
                is_current = (getattr(c, "target_id", None) == f.id)
                d = dist_to_field(c, centers[f.id])
                return (not is_current, d)
            assigned_drones.sort(key=keep_key)
            keep_set = set(assigned_drones[:cap])
            # Reassign extras to idle
            for c in assigned_drones[cap:]:
                assignments[c] = idle_group

        # Finally, assign every component via environment.assign_group
        for c in components:
            group = assignments.get(c, idle_group)
            # Safety: ensure group is present in group_ids; else fallback to idle_group
            if group not in group_ids:
                group = idle_group
            environment.assign_group(c, group)
```