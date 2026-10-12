from math import hypot
from typing import List, Dict, Set
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Always fully protect the highest-threat field using closest drones (preserve existing targeting drones).
        - Use remaining drones to fully protect other fields greedily by threat_per_drone (threat_level / drones_needed).
        - If drones remain and no full protection possible, assign remaining drones to fields with highest marginal benefit
          (heuristic: threat_level / (1 + assigned_count_for_field)) to give partial protection where it helps most.
        - Assign unassigned drones to "idle".
        """
        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_point(drone, point):
            dx = drone.location.x - point[0]
            dy = drone.location.y - point[1]
            return hypot(dx, dy)

        # Validate group names
        idle_group = "idle"
        # set of protecting groups available (should correspond to threatened fields)
        protecting_groups = {g for g in group_ids if g.startswith("protecting ")}

        # Prepare component index mapping (components may not be hashable)
        n = len(components)
        indices = list(range(n))

        # Build list of threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for comp in components:
                target = idle_group if idle_group in group_ids else group_ids[0]
                environment.assign_group(comp, target)
            return

        # Sort fields to pick the top field (highest threat_level, tie-break by id)
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top_field = threatened_fields[0]

        # Precompute field centers and required drones
        field_centers = {f.id: field_center(f) for f in threatened_fields}
        def required_for(field):
            try:
                return max(0, int(field.drones_for_full_protection))
            except Exception:
                return 0

        required_map = {f.id: required_for(f) for f in threatened_fields}

        # Map current targeting: indices of drones that currently target each field id
        current_targeting: Dict[str, List[int]] = {}
        for i, comp in enumerate(components):
            tid = comp.target_id
            if tid is None:
                continue
            current_targeting.setdefault(tid, []).append(i)

        # Assigned mapping: index -> field.id (which field's protecting group we will assign)
        assigned_to_field: Dict[int, str] = {}

        # 1) Handle top field: preserve drones already targeting it, and add closest drones until required
        top_id = top_field.id
        top_required = required_map[top_id]
        already_top = list(current_targeting.get(top_id, []))
        # Keep all already targeting (even if more than required), per instruction "if already fully protected, keep drones there"
        for idx in already_top:
            assigned_to_field[idx] = top_id

        # Compute how many more needed (only if len(already_top) < required)
        additional_needed = max(0, top_required - len(already_top))
        # Candidate drones for assignment: those not already assigned
        unassigned = [i for i in indices if i not in assigned_to_field]
        # Sort candidates by distance to top field center
        center_top = field_centers[top_id]
        unassigned.sort(key=lambda i: dist_to_point(components[i], center_top))
        for i in unassigned[:additional_needed]:
            assigned_to_field[i] = top_id

        # Update unassigned list after top assignment
        unassigned = [i for i in indices if i not in assigned_to_field]

        # 2) For other fields, try to fully protect as many as possible.
        other_fields = [f for f in threatened_fields if f.id != top_id]

        # For each other field, compute currently assigned_count (preserve current targeting)
        # and drones_needed to reach full protection
        field_state = {}
        for f in other_fields:
            fid = f.id
            existing = [i for i in current_targeting.get(fid, []) if i not in assigned_to_field]
            assigned_count = len(existing)
            needed = max(0, required_map[fid] - assigned_count)
            # We'll keep existing drones assigned to their field
            for idx in existing:
                assigned_to_field[idx] = fid
            field_state[fid] = {
                "field": f,
                "assigned_count": assigned_count,
                "needed": needed,
                "center": field_centers[fid],
                "threat": f.threat_level
            }

        # Refresh unassigned
        unassigned = [i for i in indices if i not in assigned_to_field]

        # Greedy full protection: prioritize by threat_per_drone = threat / max(1, needed)
        # Only consider fields with needed > 0
        candidates_full = [s for s in field_state.values() if s["needed"] > 0]
        # If a field already has needed == 0 it is already fully protected (we assigned existing drones)
        candidates_full.sort(key=lambda s: (- (s["threat"] / max(1, s["needed"])), str(s["field"].id)))

        for s in candidates_full:
            needed = s["needed"]
            if needed <= 0:
                continue
            if not unassigned:
                break
            # pick closest 'needed' drones from unassigned to this field
            center = s["center"]
            unassigned.sort(key=lambda i: dist_to_point(components[i], center))
            take = min(len(unassigned), needed)
            for i in unassigned[:take]:
                assigned_to_field[i] = s["field"].id
            # remove taken from unassigned
            unassigned = [i for i in unassigned if i not in assigned_to_field]

        # 3) If drones remain, assign them to fields for partial protection (marginal benefit heuristic)
        if unassigned:
            # Build list of candidate fields that could benefit (all threatened fields)
            benefit_fields = {}
            # Count how many we've assigned so far to each field (including preserved current targeting)
            assigned_counts: Dict[str, int] = {}
            for fid in [f.id for f in threatened_fields]:
                assigned_counts[fid] = sum(1 for idx, fid2 in assigned_to_field.items() if fid2 == fid)
            for f in threatened_fields:
                fid = f.id
                # marginal benefit heuristic: threat / (1 + assigned_count)
                assigned = assigned_counts.get(fid, 0)
                marginal = f.threat_level / (1 + assigned) if f.threat_level and f.threat_level > 0 else 0
                benefit_fields[fid] = {
                    "field": f,
                    "center": field_centers[fid],
                    "marginal": marginal
                }
            # For each remaining drone, pick the field with highest marginal and assign drone nearest to that field
            # Recompute marginal as assigned_counts change
            for _ in list(unassigned):
                # choose field with max marginal (tie-break by id)
                best_fid = max(benefit_fields.keys(), key=lambda fid: (benefit_fields[fid]["marginal"], str(fid)))
                # assign the closest drone from unassigned to best_fid
                center = benefit_fields[best_fid]["center"]
                unassigned.sort(key=lambda i: dist_to_point(components[i], center))
                if not unassigned:
                    break
                i = unassigned.pop(0)
                assigned_to_field[i] = best_fid
                # update assigned_counts and marginal for that field
                assigned_counts[best_fid] = assigned_counts.get(best_fid, 0) + 1
                # update marginal for that field
                fobj = benefit_fields[best_fid]["field"]
                benefit_fields[best_fid]["marginal"] = fobj.threat_level / (1 + assigned_counts[best_fid])

        # 4) Finally, assign each component to corresponding group or idle
        for idx, comp in enumerate(components):
            if idx in assigned_to_field:
                fid = assigned_to_field[idx]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    # fallback: pick any protecting group or idle
                    fallback = next(iter(protecting_groups), idle_group if idle_group in group_ids else group_ids[0])
                    environment.assign_group(comp, fallback)
            else:
                # assign to idle (or fallback)
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0])