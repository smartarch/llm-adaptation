from math import sqrt, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    SPEED = 2.0  # drone speed units per time step

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_group = {}
        self.stable_steps = defaultdict(int)
        self.last_step = None

    def _comp_key(self, comp):
        return getattr(comp, "id", None) if getattr(comp, "id", None) is not None else id(comp)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, comp, field):
        cx, cy = self._field_center(field)
        dx = getattr(comp.location, "x", 0) - cx
        dy = getattr(comp.location, "y", 0) - cy
        return sqrt(dx*dx + dy*dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step bookkeeping
        if self.last_step is None or step != self.last_step:
            self.last_step = step

        def protecting_name(fid):
            return f"protecting {fid}"

        # Gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            idle_gid = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
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

        # Sort fields by threat descending
        fields.sort(key=lambda f: (-f.threat_level, f.id))

        total_drones = len(components)
        available = set(components)
        selected = {}  # comp -> group

        # scoring helpers
        def effective_arrival(comp, field, group_name):
            dist = self._distance(comp, field)
            arrival = dist / self.SPEED
            ck = self._comp_key(comp)
            stability_bonus = min(self.stable_steps.get(ck, 0), 4) * 0.6
            prev_group = self.last_group.get(ck)
            same_group_bonus = 1.5 if prev_group == group_name else 0.0
            target_bonus = 1.0 if getattr(comp, "target_id", None) == field.id else 0.0
            protecting_bonus = 1.5 if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == field.id else 0.0
            eff = arrival - (stability_bonus + same_group_bonus + target_bonus + protecting_bonus)
            return max(0.0, eff)

        def pick_k(avail, field, group_name, k):
            if k <= 0:
                return []
            scored = []
            for c in avail:
                scored.append((effective_arrival(c, field, group_name), c))
            scored.sort(key=lambda x: x[0])
            return [c for _, c in scored[:k]]

        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Prepare caps for fields (group_name -> cap)
        field_caps = {}
        field_by_gid = {}
        for f in fields:
            gid = protecting_name(f.id)
            field_caps[gid] = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            field_by_gid[gid] = f

        # Always protect top field fully if possible
        top_field = fields[0]
        top_gid = protecting_name(top_field.id)
        required_top = field_caps.get(top_gid, 0)

        if top_gid not in group_ids:
            # fallback: assign idle
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

        allocate_top = min(required_top, len(available))
        picked_top = pick_k(available, top_field, top_gid, allocate_top)
        for c in picked_top:
            selected[c] = top_gid
            available.discard(c)

        protecting_count = sum(1 for g in selected.values() if g != idle_group)
        min_protectors_target = ceil(total_drones / 2.0)

        # Try to fully protect additional fields greedily based on benefit = threat / cap
        rest_fields = fields[1:]
        rest_fields = [f for f in rest_fields if field_caps.get(protecting_name(f.id), 0) > 0]
        rest_fields.sort(key=lambda f: (- (f.threat_level / max(1, getattr(f, "drones_for_full_protection", 1))), -f.threat_level, f.id))

        for f in rest_fields:
            if not available:
                break
            if protecting_count >= min_protectors_target:
                break
            gid = protecting_name(f.id)
            cap = field_caps.get(gid, 0)
            # number already assigned to gid
            already = sum(1 for grp in selected.values() if grp == gid)
            need = cap - already
            if need <= 0:
                continue
            if len(available) >= need:
                picked = pick_k(available, f, gid, need)
                if len(picked) < need:
                    continue
                for c in picked:
                    selected[c] = gid
                    available.discard(c)
                protecting_count += need
            else:
                # not enough to fully protect this field; skip (we prefer full protections)
                continue

        # If we still have fewer than half drones protecting, choose at most one field to partially protect
        chosen_partial_gid = None
        if protecting_count < min_protectors_target and available:
            # Candidate fields with remaining capacity
            candidates = []
            for f in fields:
                gid = protecting_name(f.id)
                cap = field_caps.get(gid, 0)
                already = sum(1 for grp in selected.values() if grp == gid)
                remaining_cap = max(0, cap - already)
                if remaining_cap <= 0:
                    continue
                # average effective arrival of available drones to this field
                effs = [effective_arrival(c, f, gid) for c in available]
                if not effs:
                    continue
                avg_eff = sum(effs) / len(effs)
                priority = (getattr(f, "threat_level", 0) / max(1, cap)) - (avg_eff * 0.05)
                candidates.append((priority, f, remaining_cap, gid))
            if candidates:
                candidates.sort(key=lambda x: -x[0])
                _, chosen_field, rem_cap, chosen_gid = candidates[0]
                need = min_protectors_target - protecting_count
                assign_count = min(len(available), rem_cap, need)
                if assign_count > 0:
                    picked = pick_k(available, chosen_field, chosen_gid, assign_count)
                    for c in picked:
                        selected[c] = chosen_gid
                        available.discard(c)
                    protecting_count += assign_count
                    chosen_partial_gid = chosen_gid

        # Remaining drones: do NOT create new partials.
        # Preserve a drone's previous protecting group only if:
        # - it is the chosen_partial_gid and there is capacity left for that group, or
        # - the group is already fully protected by our selected assignments (so preserving won't create new partial).
        # Otherwise send drone to idle.
        assigned_counts = defaultdict(int)
        for c, g in selected.items():
            assigned_counts[g] += 1

        for c in list(available):
            ck = self._comp_key(c)
            prev = self.last_group.get(ck)
            assigned = False
            if prev and prev.startswith("protecting ") and prev in field_caps:
                cap = field_caps[prev]
                already = assigned_counts.get(prev, 0)
                # if group is fully protected already, we must not add more (would overprotect)
                if already >= cap:
                    assigned = False
                else:
                    # allow only if prev is the chosen partial group (we permit expanding that one up to cap)
                    if prev == chosen_partial_gid:
                        selected[c] = prev
                        assigned_counts[prev] += 1
                        assigned = True
            if not assigned:
                selected[c] = idle_group
            if c in available:
                available.discard(c)

        # Final safety: ensure no group overprotected; trim extras by moving to idle
        group_to_comps = defaultdict(list)
        for comp, gid in selected.items():
            group_to_comps[gid].append(comp)

        for gid, comps in list(group_to_comps.items()):
            if gid.startswith("protecting ") and gid in field_caps:
                cap = field_caps[gid]
                if len(comps) > cap:
                    # choose which to keep: prefer lower effective arrival and those that were already in that group
                    f = field_by_gid.get(gid)
                    comps_sorted = sorted(comps, key=lambda c: (effective_arrival(c, f, gid), 0 if self.last_group.get(self._comp_key(c)) == gid else 1))
                    keep = comps_sorted[:cap]
                    remove = comps_sorted[cap:]
                    for c in remove:
                        selected[c] = idle_group
                    group_to_comps[gid] = keep

        # Assign and update history
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