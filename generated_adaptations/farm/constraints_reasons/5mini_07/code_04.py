from math import sqrt, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    SPEED = 2.0  # drone speed

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track last assigned group per component
        self.last_group = {}
        # consecutive steps a drone stayed in the same group
        self.stable_steps = defaultdict(int)
        self.last_step = None

    def _comp_key(self, comp):
        # Use a stable identifier if available, else python id
        return getattr(comp, "id", None) if getattr(comp, "id", None) is not None else id(comp)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, comp, field):
        cx, cy = self._field_center(field)
        dx = getattr(comp.location, "x", 0) - cx
        dy = getattr(comp.location, "y", 0) - cy
        return sqrt(dx*dx + dy*dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Update step bookkeeping
        if self.last_step is None or step != self.last_step:
            self.last_step = step

        def protecting_name(fid):
            return f"protecting {fid}"

        # Prepare list of candidate fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # no threats: assign everyone to idle
            idle_gid = "idle" if "idle" in group_ids else group_ids[0]
            for comp in components:
                environment.assign_group(comp, idle_gid)
                ck = self._comp_key(comp)
                prev = self.last_group.get(ck)
                if prev == idle_gid:
                    self.stable_steps[ck] += 1
                else:
                    self.stable_steps[ck] = 0
                self.last_group[ck] = idle_gid
            return

        # Sort fields by threat desc (primary), then by id stable order
        fields.sort(key=lambda f: (-f.threat_level, f.id))

        total_drones = len(components)
        comp_set = set(components)

        # Helper: effective arrival time score for selecting drones for a particular field/group
        def effective_arrival(comp, field, group_name):
            # base arrival time
            dist = self._distance(comp, field)
            arrival = dist / self.SPEED
            ck = self._comp_key(comp)
            # stability bonus: reduce effective arrival for stable drones (bounded)
            stability_bonus = min(self.stable_steps.get(ck, 0), 4) * 0.6  # seconds
            # prefer drones already assigned to this group (stronger bonus)
            prev_group = self.last_group.get(ck)
            same_group_bonus = 1.5 if prev_group == group_name else 0.0
            # prefer drones that currently target or protect this field
            target_bonus = 1.0 if getattr(comp, "target_id", None) == field.id else 0.0
            protecting_bonus = 1.5 if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == field.id else 0.0
            # combine to effective arrival (lower is better)
            eff = arrival - (stability_bonus + same_group_bonus + target_bonus + protecting_bonus)
            # ensure non-negative floor to keep ordering sensible
            return max(0.0, eff)

        # pick k best drones from available by minimal effective arrival
        def pick_k(avail, field, group_name, k):
            if k <= 0:
                return []
            scored = []
            for c in avail:
                scored.append((effective_arrival(c, field, group_name), c))
            scored.sort(key=lambda x: x[0])
            picked = [c for _, c in scored[:k]]
            return picked

        # prepare group ids check
        # We must only create groups for fields with threat>0; protecting_name earlier used
        # Ensure 'idle' group exists fallback to first group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # We'll build selected_assignments mapping comps to group names
        selected = {}
        available = set(comp_set)

        # Always protect the top field fully if possible
        top_field = fields[0]
        top_group = protecting_name(top_field.id)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        required_top = max(0, required_top)

        # If required_top is 0, there's nothing to assign; still keep top_group valid check
        if top_group not in group_ids:
            # As a fallback (shouldn't happen), assign all idle
            for c in components:
                environment.assign_group(c, idle_group)
                ck = self._comp_key(c)
                prev = self.last_group.get(ck)
                if prev == idle_group:
                    self.stable_steps[ck] += 1
                else:
                    self.stable_steps[ck] = 0
                self.last_group[ck] = idle_group
            return

        # If not enough drones to meet required_top, use them all (can't do better)
        allocate_top = min(required_top, len(available))
        # pick allocate_top drones minimizing effective arrival, but prefer drones already in that group
        picked_top = pick_k(available, top_field, top_group, allocate_top)
        for c in picked_top:
            selected[c] = top_group
            available.discard(c)

        protecting_count = sum(1 for g in selected.values() if g != idle_group)

        # Next, try to fully protect additional fields based on benefit metric:
        # benefit = threat_level / drones_for_full_protection
        rest_fields = fields[1:]
        # filter out fields with zero drones_for_full_protection (can't assign)
        rest_fields = [f for f in rest_fields if int(getattr(f, "drones_for_full_protection", 0)) > 0]
        rest_fields.sort(key=lambda f: (- (f.threat_level / max(1, getattr(f,"drones_for_full_protection"))), -f.threat_level, f.id))

        # Aim to have at least half drones protecting
        min_protectors_target = ceil(total_drones / 2.0)

        for f in rest_fields:
            if not available:
                break
            req = int(getattr(f, "drones_for_full_protection", 0))
            req = max(0, req)
            if req == 0:
                continue
            # if we already reached min target, don't add new full protections unless it increases total protected threat significantly
            if protecting_count >= min_protectors_target:
                break
            if len(available) >= req:
                group_name = protecting_name(f.id)
                if group_name not in group_ids:
                    continue
                picked = pick_k(available, f, group_name, req)
                if len(picked) < req:
                    # not enough available high-quality picks; skip
                    continue
                for c in picked:
                    selected[c] = group_name
                    available.discard(c)
                protecting_count += req
            else:
                # not enough to fully protect; skip for now, we'll consider partial later
                continue

        # If we still have fewer than half drones protecting, assign remaining drones to partial protection of the best remaining field.
        if protecting_count < min_protectors_target and available:
            # pick best candidate among fields (including top_field if still needs drones) by weighted priority:
            # priority = threat_level / max(1, drones_for_full_protection) but also prefer closer fields overall
            candidates = []
            for f in fields:
                gname = protecting_name(f.id)
                if gname not in group_ids:
                    continue
                # number already assigned to this field
                already = sum(1 for grp in selected.values() if grp == gname)
                cap = max(0, int(getattr(f, "drones_for_full_protection", 0)) - already)
                if cap <= 0:
                    continue
                # compute average effective arrival of available drones to approximate closeness
                sample = []
                for c in available:
                    sample.append(effective_arrival(c, f, gname))
                if not sample:
                    continue
                avg_eff = sum(sample) / len(sample)
                priority = (getattr(f, "threat_level", 0) / max(1, getattr(f, "drones_for_full_protection", 1))) - (avg_eff * 0.05)
                candidates.append((priority, f, cap, gname))
            # pick the best candidate
            if candidates:
                candidates.sort(key=lambda x: -x[0])
                _, chosen_field, cap, chosen_group = candidates[0]
                # How many drones do we need to reach min_protectors_target?
                need = min_protectors_target - protecting_count
                assign_count = min(len(available), cap, need)
                if assign_count > 0:
                    picked = pick_k(available, chosen_field, chosen_group, assign_count)
                    for c in picked:
                        selected[c] = chosen_group
                        available.discard(c)
                    protecting_count += assign_count

        # Any remaining drones: prefer to keep them in their last group if that group corresponds to a threatened field and that field isn't overprotected.
        # Otherwise assign them to idle.
        # Build mapping of how many assigned per protecting group so far
        assigned_counts = defaultdict(int)
        for c, g in selected.items():
            assigned_counts[g] += 1

        for c in list(available):
            ck = self._comp_key(c)
            prev = self.last_group.get(ck)
            assigned = False
            if prev and prev.startswith("protecting "):
                # check if that field is still threatened and group exists and we won't overprotect
                # get field id from group name
                try:
                    _, fid = prev.split(" ", 1)
                    gid = prev
                    # find corresponding field
                    fld = next((f for f in fields if str(f.id) == fid), None)
                    if fld is not None:
                        cap = int(getattr(fld, "drones_for_full_protection", 0))
                        already = assigned_counts.get(gid, 0)
                        if already < cap:
                            # keep this drone in its previous protecting group to preserve stability
                            selected[c] = gid
                            assigned_counts[gid] += 1
                            assigned = True
                except Exception:
                    assigned = False
            if not assigned:
                # default to idle
                selected[c] = idle_group
            if c in available:
                available.discard(c)

        # Make sure no group is overprotected
        # For each protecting group, if we accidentally assigned more than drones_for_full_protection (shouldn't happen), trim extras
        # Build reverse map group -> list of comps
        group_to_comps = defaultdict(list)
        for comp, gid in selected.items():
            group_to_comps[gid].append(comp)

        for f in fields:
            gid = protecting_name(f.id)
            if gid in group_to_comps:
                cap = max(0, int(getattr(f, "drones_for_full_protection", 0)))
                comps = group_to_comps[gid]
                if len(comps) > cap:
                    # decide which to keep: prefer those with lower effective arrival and those that were already in same group
                    comps_sorted = sorted(comps, key=lambda c: (effective_arrival(c, f, gid), 0 if self.last_group.get(self._comp_key(c))==gid else 1))
                    keep = comps_sorted[:cap]
                    remove = comps_sorted[cap:]
                    for c in remove:
                        # send to idle (or try to reassign to other fields if beneficial -- but to keep it simple, idle)
                        selected[c] = idle_group
                    group_to_comps[gid] = keep

        # Final assignment via environment.assign_group and update stability info
        for comp in components:
            gid = selected.get(comp, idle_group)
            environment.assign_group(comp, gid)
            ck = self._comp_key(comp)
            prev = self.last_group.get(ck)
            if prev == gid:
                self.stable_steps[ck] += 1
            else:
                self.stable_steps[ck] = 0
            self.last_group[ck] = gid