# SmartFarmAdaptation
#
# Reasoning and improved strategy:
# - Goal recap: Always fully protect the single highest-threat field using the closest drones,
#   and keep drones protecting a field there where appropriate. After the top field is fully
#   protected, use remaining drones to fully protect additional fields where possible.
# - Observed issues to address:
#   * Top-field coverage was only ~0.7 previously because we avoided reassigning protecting drones.
#   * We should allow reassigning drones from lower-threat fields when necessary to fully cover
#     a much higher-threat field, but avoid pulling from equally or more important fields.
#   * Prefer drones that are idle or already moving/protecting the target field; prefer nearby drones.
# - Strategy improvements implemented:
#   1) Treat drones protecting or moving to the target field as committed and count them.
#   2) When additional drones are needed for a field, select drones minimizing a cost:
#        cost = distance^2 + penalty
#      where penalty depends on the drone's current assignment:
#        - idle: penalty 0
#        - moving_to_field (other target): moderate penalty scaled by (other_field_threat / target_field_threat)
#        - protecting (other target): larger penalty scaled by (other_field_threat / target_field_threat)
#      This allows stealing drones from low-threat fields to defend a much higher-threat field,
#      while discouraging stealing from similarly or more important fields.
#   3) After securing the highest-threat field, repeat the greedy allocation for remaining fields
#      in descending threat order to fully protect as many as possible (maximizing coverage where it matters).
#   4) Explicitly assign every drone on each step (either to a protecting group or to "idle").
#
# Expected effects:
# - Better coverage for the highest-threat field (move coverage closer to 1.0),
#   while still keeping average protecting drones high and avoiding excessive thrashing.
#
# Implementation notes:
# - Distance is measured to the field center; drone speed (2) only affects arrival time monotonic with distance,
#   so distance^2 is sufficient for ranking.
# - All group names used are exactly "idle" and "protecting {field.id}".
# - If a protecting group name is not present in group_ids, the code skips assigning to that group for that field.
#
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center_of_field(field):
            try:
                return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)
            except Exception:
                return (0.0, 0.0)

        def dist2(loc, point):
            try:
                dx = getattr(loc, "x", 0.0) - point[0]
                dy = getattr(loc, "y", 0.0) - point[1]
                return dx * dx + dy * dy
            except Exception:
                return float("inf")

        # Prepare mapping of fields by id for quick lookup
        fields = list(environment.fields)
        fields_by_id = {getattr(f, "id"): f for f in fields}

        # List of threatened fields (threat_level > 0), sorted by descending threat
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]
        threatened.sort(key=lambda f: (f.threat_level, str(getattr(f, "id", ""))), reverse=True)

        # Group name for idle (fallback to first group if not present)
        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else "idle"

        # If no threatened fields, idle everyone explicitly
        if not threatened:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Component bookkeeping
        comp_list = list(components)
        comp_key = lambda c: id(c)
        comp_by_key = {comp_key(c): c for c in comp_list}
        assigned = {}  # comp_key -> group_name

        # Penalty base values (tunable)
        BASE_PROTECT_PENALTY = 2000.0   # base penalty for pulling a drone that is protecting another field
        BASE_MOVING_PENALTY = 150.0     # base penalty for pulling a drone moving to another field
        # Reasoning: PROTECT penalty is larger to discourage taking from other protecting drones unless donor field is much less important.

        # Helper to compute penalty for reassigning a drone currently assigned to some other field
        def reassignment_penalty(comp, target_field):
            st = getattr(comp, "state", None)
            tid = getattr(comp, "target_id", None)
            # If drone is idle or has no relevant target, no penalty
            if st is None:
                return 0.0
            if st in ("protecting", "moving_to_field") and tid == getattr(target_field, "id"):
                return 0.0
            # If moving or protecting to another field, compute penalty scaled by relative threat
            if tid is not None and tid in fields_by_id:
                donor_field = fields_by_id[tid]
                donor_threat = getattr(donor_field, "threat_level", 0.0)
            else:
                donor_threat = 0.0
            target_threat = getattr(target_field, "threat_level", 0.0) or 1e-6
            threat_ratio = donor_threat / target_threat  # if donor lower-threat, ratio small => penalty small

            if st == "protecting":
                # Larger base penalty scaled by threat ratio; low donor threat -> small penalty
                return BASE_PROTECT_PENALTY * max(0.0, threat_ratio)
            elif st == "moving_to_field":
                return BASE_MOVING_PENALTY * max(0.0, threat_ratio)
            else:
                # idle or other states: no penalty
                return 0.0

        # Utility: choose drones for a specific field (may include reassigning from others)
        def choose_drones_for_field(field, available_keys, needed):
            if needed <= 0:
                return []

            center = center_of_field(field)
            chosen = []

            # First, include drones already protecting or moving to this field among available
            committed = []
            for k in list(available_keys):
                comp = comp_by_key[k]
                st = getattr(comp, "state", None)
                tid = getattr(comp, "target_id", None)
                if (st == "protecting" or st == "moving_to_field") and tid == getattr(field, "id"):
                    committed.append(k)

            for k in committed:
                available_keys.remove(k)
                chosen.append(k)
                if len(chosen) >= needed:
                    return chosen[:needed]

            # Need more drones: compute cost for remaining available drones
            scored = []
            for k in available_keys:
                comp = comp_by_key[k]
                d2 = dist2(getattr(comp, "location", None), center)
                penalty = reassignment_penalty(comp, field)
                score = d2 + penalty
                scored.append((score, k))

            # Sort by score and pick required number
            scored.sort(key=lambda x: (x[0], x[1]))
            for _, k in scored[:max(0, needed - len(chosen))]:
                chosen.append(k)

            # Remove chosen from available_keys
            for k in chosen:
                if k in available_keys:
                    available_keys.remove(k)

            return chosen[:needed]

        # Main allocation:
        # 1) Ensure highest-threat field fully protected first (must be done).
        # 2) Then greedily protect other fields in descending threat order using remaining drones.
        total_keys = list(comp_by_key.keys())
        available_keys = set(total_keys)

        # Process top field first
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # If protecting group not available for this field, we cannot assign; idle everyone
            for comp in comp_list:
                environment.assign_group(comp, idle_group)
            return

        top_needed = int(getattr(top_field, "drones_for_full_protection", 0))
        # Choose drones for top field
        top_chosen = choose_drones_for_field(top_field, available_keys, top_needed)
        # Assign chosen to protecting group for top field
        for k in top_chosen:
            assigned[k] = top_group

        # If we still don't have enough (not enough drones overall), we've done our best; continue to assign others
        # Now process remaining fields in descending threat order (skipping top_field which we've done)
        for field in threatened[1:]:
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            chosen = choose_drones_for_field(field, available_keys, required)
            for k in chosen:
                assigned[k] = group_name
            # continue to next field

        # Any drones still available -> assign to idle
        for k in list(available_keys):
            assigned[k] = idle_group

        # Ensure drones that were assigned to protecting groups but were originally committed (protecting/moving to that field)
        # are explicitly assigned as well (they should be in 'assigned' already if chosen; but commit case might have removed from available_keys)
        # For safety, for any comp not yet assigned, place them idle
        for k in total_keys:
            if k not in assigned:
                assigned[k] = idle_group

        # Final: map keys back to components and call environment.assign_group
        for k, group in assigned.items():
            comp = comp_by_key.get(k)
            if comp is None:
                continue
            environment.assign_group(comp, group)