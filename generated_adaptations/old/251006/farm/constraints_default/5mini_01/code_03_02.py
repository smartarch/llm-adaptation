# Improved adaptation strategy (reasoning described here as comments):
#
# Goal: further reduce damage by (a) guaranteeing the highest-threat field is fully protected by the closest drones,
# (b) using remaining drones to increase actual protection coverage across other threatened fields, and
# (c) minimizing unnecessary drone movement by preferring to keep drones where they already protect or are already moving.
#
# Key ideas:
# 1. Primary (highest-threat) field: as required, fully protect it using the closest drones overall. This may reassign
#    drones that were protecting lower-priority fields if they are closer to the primary.
# 2. Secondary fields: after primary is satisfied, attempt to bring other fields up to full protection in descending
#    threat order, by assigning the closest remaining drones to each field until its required count is reached.
#    When counting already-committed drones for a field, include drones that started the step protecting/moving to it
#    (except those taken for the primary).
# 3. If there are leftover drones after attempting to fully protect fields, assign them greedily to fields where they
#    give the most "value" — measured as threat_level / distance — so that partial protection still targets high-threat
#    and nearby fields.
# 4. Assign any drones that have no useful field to "idle".
#
# This balances strict priority for the most-threatened field while maximizing the number of drones actually protecting
# fields and avoiding excessive, pointless movement.
#
# Implementation notes:
# - Use field centers ((left+right)/2, (top+bottom)/2) to compute distances.
# - Each component is assigned exactly once via environment.assign_group.
# - Group names used: "idle" and "protecting {field.id}" for fields with threat_level > 0 (only if present in group_ids).
# - Deterministic tie-breaking: use component id and field id ordering where needed.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"

        all_fields = getattr(environment, "fields", []) or []
        # Consider only fields with positive threat
        fields_with_threat = [f for f in all_fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not fields_with_threat:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Helpers
        def field_center(f):
            left = getattr(f, "left", 0.0)
            right = getattr(f, "right", 0.0)
            top = getattr(f, "top", 0.0)
            bottom = getattr(f, "bottom", 0.0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        def dist(comp, center):
            loc = getattr(comp, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", 0.0)
            y = getattr(loc, "y", 0.0)
            return math.hypot(x - center[0], y - center[1])

        # Sort fields by descending threat_level, tie-break by id string for determinism
        def field_key(f):
            return (-getattr(f, "threat_level", 0.0), str(getattr(f, "id", "")))
        fields_sorted = sorted(fields_with_threat, key=field_key)

        # Map components by stable id
        comp_by_cid = {id(c): c for c in components}
        all_cids = list(comp_by_cid.keys())
        unassigned_cids = set(all_cids)
        assignments = {}  # cid -> group_name

        # Precompute committed drones per field (those protecting or moving_to_field at start)
        committed = {}  # field_id -> set of cids
        for f in fields_sorted:
            committed[f.id] = set()
        for cid, comp in comp_by_cid.items():
            state = getattr(comp, "state", None)
            target_id = getattr(comp, "target_id", None)
            if state in ("protecting", "moving_to_field") and target_id in committed:
                committed[target_id].add(cid)

        # ---- PRIMARY field: ensure full protection with closest drones ----
        primary_field = fields_sorted[0]
        primary_group = f"protecting {getattr(primary_field, 'id')}"
        # Defensive: if primary group not available, assign all to idle
        if primary_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        needed_primary = int(getattr(primary_field, "drones_for_full_protection", 0))
        primary_center = field_center(primary_field)

        # Choose the closest drones overall (including those already committed to any field) to fill primary
        # Deterministic sort by (distance, cid)
        all_cids_sorted_by_primary = sorted(all_cids, key=lambda cid: (dist(comp_by_cid[cid], primary_center), cid))
        chosen_primary = all_cids_sorted_by_primary[:needed_primary]

        # Assign chosen primary and remove them from unassigned and from other fields' committed sets
        for cid in chosen_primary:
            assignments[cid] = primary_group
            if cid in unassigned_cids:
                unassigned_cids.remove(cid)
        # Remove chosen_primary from committed sets of other fields
        for fid, s in committed.items():
            for cid in chosen_primary:
                if cid in s:
                    s.remove(cid)

        # ---- SECONDARY fields: try to fully protect each in descending threat order using closest remaining drones ----
        for field in fields_sorted[1:]:
            group_name = f"protecting {getattr(field, 'id')}"
            if group_name not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            center = field_center(field)

            # Current committed for this field (after removals due to primary)
            currently_committed = set(committed.get(field.id, set()))  # cids
            committed_count = len(currently_committed)

            if committed_count >= required:
                # Keep exactly required committed (prefer those actually protecting first if possible).
                # Identify protecting ones among committed to prefer them.
                committed_list = list(currently_committed)
                def pref_key(cid):
                    comp = comp_by_cid[cid]
                    state = getattr(comp, "state", None)
                    state_score = 0 if state == "protecting" else 1
                    return (state_score, dist(comp, center), cid)
                keep = sorted(committed_list, key=pref_key)[:required]
                # assign keep
                for cid in keep:
                    assignments[cid] = group_name
                    if cid in unassigned_cids:
                        unassigned_cids.remove(cid)
                # Any other committed ones that we didn't keep remain available (we did not assign them now)
                for cid in currently_committed:
                    if cid not in keep and cid not in assignments:
                        # leave them unassigned to be used for other fields or idle
                        if cid in unassigned_cids:
                            # already unassigned
                            pass
                        else:
                            # If they were not in unassigned but not chosen, make sure they'll be considered unassigned
                            unassigned_cids.add(cid)
                continue

            # Need more drones to reach full protection
            need_more = required - committed_count

            # Choose closest from unassigned_cids
            available_cids = list(unassigned_cids)
            available_cids_sorted = sorted(available_cids, key=lambda cid: (dist(comp_by_cid[cid], center), cid))
            chosen_extra = available_cids_sorted[:need_more]
            # Assign all committed + chosen_extra to this field
            chosen_all = list(currently_committed) + chosen_extra
            # If we don't have enough (i.e., committed_count + len(chosen_extra) < required), we still assign what we have
            # because partial protection is better than idle (we aim to use drones). This differs from previous strict approach.
            # Assign chosen_all (but limit to required to avoid over-allocation)
            chosen_final = chosen_all[:required]
            for cid in chosen_final:
                assignments[cid] = group_name
                if cid in unassigned_cids:
                    unassigned_cids.remove(cid)
            # If some previously committed cids were not included (excess), leave them available (add to unassigned)
            for cid in currently_committed:
                if cid not in chosen_final and cid not in assignments:
                    unassigned_cids.add(cid)

        # ---- Leftover drones: assign to best-value field (threat/distance) or idle if none ----
        if unassigned_cids:
            # Precompute centers and ensure group exists
            candidate_fields = []
            for f in fields_sorted:
                gname = f"protecting {getattr(f, 'id')}"
                if gname in group_ids:
                    candidate_fields.append((f, field_center(f)))
            # For each remaining drone, pick field maximizing threat_level / (distance + eps)
            eps = 1e-6
            for cid in list(unassigned_cids):
                comp = comp_by_cid[cid]
                best_score = 0.0
                best_field_group = None
                for f, center in candidate_fields:
                    d = dist(comp, center)
                    # score: higher threat and closer distance is better
                    score = getattr(f, "threat_level", 0.0) / (d + eps)
                    if score > best_score:
                        best_score = score
                        best_field_group = f"protecting {getattr(f, 'id')}"
                # If best score is insignificantly small (e.g., all distances infinite), assign idle
                if best_field_group is None or best_score <= 0.0:
                    assignments[cid] = idle_group
                else:
                    assignments[cid] = best_field_group
                unassigned_cids.remove(cid)

        # ---- Final safety: ensure every component has an assignment, fallback to idle if missing ----
        for cid, comp in comp_by_cid.items():
            if cid not in assignments:
                assignments[cid] = idle_group

        # Perform assignments exactly once per component
        for cid, group in assignments.items():
            comp = comp_by_cid.get(cid)
            if comp is not None:
                environment.assign_group(comp, group)