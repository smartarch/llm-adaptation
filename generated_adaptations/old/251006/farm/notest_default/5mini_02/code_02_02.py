# SmartFarmAdaptation
#
# Reasoning and improved strategy:
# - Problem observed: low coverage of the most-threatened field and many drones idle or moving.
# - Required constraint: Always fully protect the highest-threat field with the closest drones.
# - Improvements implemented:
#   1) Treat drones that are already moving toward a field (state == "moving_to_field" and
#      target_id == field.id) as committed to that field (count them toward protection). This
#      reduces thrashing and leverages in-flight effort.
#   2) When selecting additional drones for a field, prefer idle or nearby drones and avoid
#      pulling away drones that are actively protecting other fields unless absolutely necessary.
#      This is implemented with small penalties for reassigning protecting/moving drones that target
#      other fields; penalties are tuned so that reassigning happens only when needed.
#   3) After fully protecting the highest-threat field (mandatory), continue to protect other
#      threatened fields in descending threat order, using remaining drones to fully protect as
#      many as possible. Partial protection still helps but we try to fully protect fields when we can.
#   4) Assign any leftover drones to "idle".
# - Expected effect:
#   * Higher coverage on the top-priority field because in-flight drones count and we minimize unnecessary reassignments.
#   * More drones actually in protecting state (we try to fully protect multiple fields).
#   * Fewer drones switching targets and less time spent moving between fields.
#
# Notes:
# - All components must be explicitly assigned each call.
# - The code is conservative about reassigning already-protecting drones by adding a penalty;
#   this adheres to the "closest drones" requirement while reducing protection churn.
# - The group names used are exactly "idle" and "protecting {field.id}" for threat_level>0 fields.
#
# Implementation below.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center_of_field(field):
            try:
                cx = (field.left + field.right) / 2.0
                cy = (field.top + field.bottom) / 2.0
                return (cx, cy)
            except Exception:
                return (0.0, 0.0)

        def dist2_to_point(loc, point):
            try:
                dx = getattr(loc, "x", 0.0) - point[0]
                dy = getattr(loc, "y", 0.0) - point[1]
                return dx * dx + dy * dy
            except Exception:
                return float("inf")

        # Build threatened fields list (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Ensure "idle" exists or pick fallback
        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else "idle"

        # If no threatened fields, idle everyone
        if not threatened_fields:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Sort fields by descending threat_level, tie-break by id for determinism
        threatened_fields.sort(key=lambda f: (f.threat_level, str(getattr(f, "id", ""))), reverse=True)

        # Prepare component lookup keys to safely use in maps (use id(comp) as stable key)
        comp_key = lambda c: id(c)
        comp_by_key = {comp_key(c): c for c in components}
        assigned = {}  # comp_key -> group_name

        # Penalty values to prefer not reassigning protecting/moving drones already committed elsewhere
        PENALTY_PROTECTING_OTHER = 1e6  # very large penalty to avoid pulling drones already protecting other fields
        PENALTY_MOVING_OTHER = 1e3      # moderate penalty for drones moving to other targets

        # Process fields in order; highest-threat first ensures the mandatory constraint.
        for idx, field in enumerate(threatened_fields):
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                # No valid group for this field in this environment; skip
                continue

            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Compute center for distance calculations
            center = center_of_field(field)

            # Identify unassigned components
            unassigned_keys = [k for k in comp_by_key.keys() if k not in assigned]

            # First, commit already-protecting and in-flight-to-this-field drones among unassigned.
            # Treat both state=="protecting" and state=="moving_to_field" with matching target_id as committed.
            committed_keys = []
            for k in list(unassigned_keys):
                comp = comp_by_key[k]
                st = getattr(comp, "state", None)
                tid = getattr(comp, "target_id", None)
                if (st == "protecting" or st == "moving_to_field") and tid == field.id:
                    committed_keys.append(k)

            # Assign committed drones to this field
            for k in committed_keys:
                assigned[k] = group_name
            required -= len(committed_keys)
            if required <= 0:
                # Field is (or will be) fully protected; move on
                continue

            # Need additional drones: choose best among remaining unassigned drones.
            # Compute cost = distance^2 + penalty (large for protecting others, moderate for moving to other target)
            candidate_keys = [k for k in unassigned_keys if k not in committed_keys]
            scored_candidates = []
            for k in candidate_keys:
                comp = comp_by_key[k]
                st = getattr(comp, "state", None)
                tid = getattr(comp, "target_id", None)
                d2 = dist2_to_point(getattr(comp, "location", None), center)

                penalty = 0.0
                # If drone is currently protecting another field, avoid reassigning unless necessary
                if st == "protecting" and tid != field.id:
                    penalty += PENALTY_PROTECTING_OTHER
                elif st == "moving_to_field" and tid is not None and tid != field.id:
                    penalty += PENALTY_MOVING_OTHER
                # Idle or moving with no specific target gets no penalty

                score = d2 + penalty
                scored_candidates.append((score, k))

            # Sort by score (lower is better) and pick up to 'required' drones
            scored_candidates.sort(key=lambda x: (x[0], x[1]))
            chosen = [k for (_, k) in scored_candidates[:required]]

            # Assign chosen drones
            for k in chosen:
                assigned[k] = group_name

            # Continue to next field (remaining drones will be used for subsequent fields)
            # Loop continues

        # After attempting to protect fields in order, assign any remaining unassigned drones to idle
        for k in comp_by_key.keys():
            if k not in assigned:
                assigned[k] = idle_group

        # Finally, perform the actual group assignments
        for k, group in assigned.items():
            comp = comp_by_key.get(k)
            # Safety: if comp is None (shouldn't happen), skip
            if comp is None:
                continue
            environment.assign_group(comp, group)