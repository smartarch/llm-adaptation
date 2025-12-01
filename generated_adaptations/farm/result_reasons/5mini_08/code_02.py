from typing import Dict, Tuple
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for smart farm drone allocation.

    Key ideas implemented:
    - Always fully protect the most threatened field using the closest drones.
    - Keep drones already protecting a fully-protected field in place.
    - Avoid overprotection by not assigning more than drones_for_full_protection to any field.
    - Use at least half of the drones for protection when feasible.
    - Prefer stability: track assignments and avoid unnecessary reassignments.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map drone_key -> (group_id, step_assigned)
        # drone_key uses id(component) (object identity)
        self._assign_info: Dict[int, Tuple[str, int]] = {}

    def _comp_key(self, comp):
        # Use object identity so we can track across calls
        return id(comp)

    def _field_group_name(self, field):
        return f"protecting {field.id}"

    def _distance_to_field_center(self, comp, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = (getattr(comp.location, "x", 0.0) - cx)
        dy = (getattr(comp.location, "y", 0.0) - cy)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Ensure we have entries for all components in our history
        for comp in components:
            key = self._comp_key(comp)
            if key not in self._assign_info:
                # try to infer group from drone state/target
                if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None):
                    inferred = f"protecting {comp.target_id}"
                    if inferred in group_ids:
                        self._assign_info[key] = (inferred, step)
                        continue
                # if moving to a field, consider it as intending to protect that field (start assignment now)
                if getattr(comp, "state", None) == "moving_to_field" and getattr(comp, "target_id", None):
                    inferred = f"protecting {comp.target_id}"
                    if inferred in group_ids:
                        self._assign_info[key] = (inferred, step)
                        continue
                # otherwise idle
                self._assign_info[key] = ("idle", step)

        # Build fields of interest (threat_level > 0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threatened fields: set all drones to idle
            for comp in components:
                environment.assign_group(comp, "idle")
                self._assign_info[self._comp_key(comp)] = ("idle", step)
            return

        # Sort fields by threat descending
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)
        most_threat_field = fields_sorted[0]

        # Helpers & book-keeping
        comp_by_key = {self._comp_key(c): c for c in components}
        total_drones = len(components)
        half_needed = math.ceil(total_drones / 2)

        # Current recorded assignments (from history) - which drones are recorded as assigned to which groups
        current_group_members: Dict[str, list] = {}
        for key, (group, assigned_step) in self._assign_info.items():
            current_group_members.setdefault(group, []).append((key, assigned_step))

        # We'll build target assignment map: group_name -> list of comp keys
        target_assignments: Dict[str, list] = {}

        used_keys = set()

        # Function to add selected comp keys to a group
        def assign_keys_to_group(group_name, keys):
            lst = target_assignments.setdefault(group_name, [])
            for k in keys:
                if k in used_keys:
                    continue
                lst.append(k)
                used_keys.add(k)

        # ---------- Step A: Handle most threatened field ----------
        most_group = self._field_group_name(most_threat_field)
        needed = int(getattr(most_threat_field, "drones_for_full_protection", 0))
        # Count currently assigned to that group according to our history
        current_members = [k for (k, s) in current_group_members.get(most_group, []) if k in comp_by_key]
        # If currently fully protected (>= needed) keep those drones (but limit to needed keeping long-tenured)
        if len(current_members) >= needed and needed > 0:
            # sort current_members by assigned_step ascending (longest-tenured first)
            entries = current_group_members.get(most_group, [])
            # filter to present drones
            present_entries = [(k, s) for (k, s) in entries if k in comp_by_key]
            present_entries.sort(key=lambda kv: kv[1])  # earlier step (longer tenure) first
            keep = [k for (k, s) in present_entries[:needed]]
            assign_keys_to_group(most_group, keep)
        else:
            # need to pick the closest drones (distance primary). Slightly prefer drones that already target this field.
            # Build candidate list of (key, distance, already_target_flag, tenure)
            candidates = []
            for key, comp in comp_by_key.items():
                dist = self._distance_to_field_center(comp, most_threat_field)
                # already targeting/protecting this field? Check history or component target
                prev_group, prev_step = self._assign_info.get(key, ("idle", step))
                already = 1 if prev_group == most_group or getattr(comp, "target_id", None) == most_threat_field.id else 0
                candidates.append((key, dist, -already, prev_step))
            # Sort by distance ascending, then prefer already-target (because -already), then by earlier prev_step
            candidates.sort(key=lambda item: (item[1], item[2], item[3]))
            chosen = [k for (k, _, _, _) in candidates[:needed]]
            assign_keys_to_group(most_group, chosen)

        # ---------- Step B: Handle other fields: try to fully protect them if resources allow ----------
        # Compute remaining drones available
        def currently_assigned_count_for_group(g):
            return len(target_assignments.get(g, []))

        remaining_capacity = total_drones - len(used_keys)
        # For other fields in descending threat (skip the first as handled)
        for field in fields_sorted[1:]:
            group = self._field_group_name(field)
            need = int(getattr(field, "drones_for_full_protection", 0))
            if need <= 0:
                continue
            # How many already planned for this group (from history and target_assignments)
            already_assigned = 0
            # consider history-members who are not yet used and belong to this group
            hist_members = [k for (k, s) in current_group_members.get(group, []) if (k in comp_by_key and k not in used_keys)]
            already_assigned += len(hist_members)
            # We can use hist_members first
            to_assign = []
            for k in hist_members:
                if len(to_assign) >= need:
                    break
                to_assign.append(k)
            if len(to_assign) < need:
                # need extra drones; check if we have enough available to reach full protection
                need_extra = need - len(to_assign)
                if remaining_capacity >= need_extra:
                    # pick closest remaining drones
                    candidates = []
                    for key, comp in comp_by_key.items():
                        if key in used_keys:
                            continue
                        # avoid picking ones we've already chosen for other groups in this round
                        prev_group, prev_step = self._assign_info.get(key, ("idle", step))
                        dist = self._distance_to_field_center(comp, field)
                        already = 1 if prev_group == group or getattr(comp, "target_id", None) == field.id else 0
                        candidates.append((key, dist, -already, prev_step))
                    candidates.sort(key=lambda item: (item[1], item[2], item[3]))
                    extras = [k for (k, _, _, _) in candidates[:need_extra]]
                    to_assign.extend(extras)
                else:
                    # Not enough resources to fully protect this field; skip it now (prefer fully protecting fewer fields)
                    to_assign = to_assign  # only historical members (if any); we won't partially protect beyond that
            # Assign what we decided for this field
            if to_assign:
                assign_keys_to_group(group, to_assign)
                remaining_capacity = total_drones - len(used_keys)

        # ---------- Step C: If fewer than half drones are protecting something, try to assign extras (without overprotecting) ----------
        currently_protecting = sum(len(v) for k, v in target_assignments.items() if k != "idle")
        if currently_protecting < half_needed:
            need_more = half_needed - currently_protecting
            # iterate fields in threat order and fill remaining capacity
            for field in fields_sorted:
                if need_more <= 0:
                    break
                group = self._field_group_name(field)
                cap = int(getattr(field, "drones_for_full_protection", 0))
                already = len(target_assignments.get(group, []))
                can_add = cap - already
                if can_add <= 0:
                    continue
                # pick up to min(can_add, need_more) closest unused drones
                candidates = []
                for key, comp in comp_by_key.items():
                    if key in used_keys:
                        continue
                    prev_group, prev_step = self._assign_info.get(key, ("idle", step))
                    dist = self._distance_to_field_center(comp, field)
                    already_flag = 1 if prev_group == group or getattr(comp, "target_id", None) == field.id else 0
                    candidates.append((key, dist, -already_flag, prev_step))
                if not candidates:
                    break
                candidates.sort(key=lambda item: (item[1], item[2], item[3]))
                to_take = min(can_add, need_more)
                extras = [k for (k, _, _, _) in candidates[:to_take]]
                if extras:
                    assign_keys_to_group(group, extras)
                    need_more -= len(extras)

        # ---------- Step D: Remaining drones -> idle ----------
        for key in comp_by_key:
            if key not in used_keys:
                assign_keys_to_group("idle", [key])

        # ---------- Step E: Enforce no overprotection (safety pass) ----------
        # Ensure no group exceeds its field capacity; if it does, free newest assignments first
        for field in fields:
            group = self._field_group_name(field)
            cap = int(getattr(field, "drones_for_full_protection", 0))
            members = target_assignments.get(group, [])
            if cap <= 0:
                # shouldn't assign here; move all back to idle
                if members:
                    for k in members:
                        used_keys.discard(k)
                    target_assignments[group] = []
                continue
            if len(members) > cap:
                # We need to drop len(members)-cap of them.
                # Prefer to keep long-tenured drones: consult assign_info timestamps
                mem_entries = []
                for k in members:
                    prev_group, prev_step = self._assign_info.get(k, ("idle", step))
                    # if drone was already in this group, use its prev_step; otherwise use current step to reflect change
                    mem_entries.append((k, prev_step))
                # sort by prev_step ascending (long-tenured first)
                mem_entries.sort(key=lambda kv: kv[1])
                keep = [k for (k, s) in mem_entries[:cap]]
                drop = [k for (k, s) in mem_entries[cap:]]
                target_assignments[group] = keep
                for k in drop:
                    used_keys.discard(k)
                    # move dropped drones to idle (will be added below if still unassigned)
        # ensure idle group list exists
        target_assignments.setdefault("idle", [])

        # Any keys that were removed from used_keys during safety pass need reassigning to idle
        for key in comp_by_key:
            assigned_somewhere = any(key in lst for lst in target_assignments.values())
            if not assigned_somewhere:
                target_assignments["idle"].append(key)

        # ---------- Step F: Commit assignments through environment.assign_group and update history ----------
        # For consistent ordering, iterate over all components and assign their computed group
        # Build reverse map key -> group
        key_to_group = {}
        for g, lst in target_assignments.items():
            for k in lst:
                key_to_group[k] = g

        for comp in components:
            k = self._comp_key(comp)
            target_group = key_to_group.get(k, "idle")
            # Sanity: only assign to allowed group ids
            if target_group not in group_ids:
                # fallback to idle if computed group not present
                target_group = "idle" if "idle" in group_ids else group_ids[0]
            environment.assign_group(comp, target_group)
            prev_group, prev_step = self._assign_info.get(k, (None, step))
            if prev_group != target_group:
                # assignment changed: update timestamp
                self._assign_info[k] = (target_group, step)
            else:
                # unchanged: keep previous timestamp
                self._assign_info[k] = (prev_group if prev_group is not None else target_group, prev_step)

        # End of assign_drones