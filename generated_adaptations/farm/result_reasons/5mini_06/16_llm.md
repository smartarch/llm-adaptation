Reasoning and adaptation strategy

Summary of goals
- Always fully protect the single most-threatened field using the drones that will arrive fastest (arrival time = distance / speed).
- Prefer drones already protecting or already moving to that field; avoid stealing protecting drones unless absolutely necessary.
- Avoid overprotection; never assign more drones to a field than drones_for_full_protection.
- Preserve persistence: drones that have been commanded and observed in the same group for multiple steps are "locked" and should not be moved unless the benefit is decisive.
- Use a simple, robust utility-based greedy allocation for remaining drones: compute a benefit per additional drone for each field that accounts for threat, required drones, and expected arrival times; allocate remaining drones to fields with highest benefit, preferring idle/moving drones.
- Maintain a soft “at least half used” guideline by assigning idle/moving drones to high-benefit fields if possible (avoid aggressive stealing).

Key improvements vs. earlier attempts
- Use arrival-time ordering (not raw distance) and discriminate between drone states (protecting, moving_to_field, idle) explicitly in selection priority.
- Use a locking/hysteresis mechanism to reduce oscillation and wasted travel.
- Use a clear steal budget and only allow stealing for the top field when necessary.
- Use a simple utility function for allocating remaining drones without complex stealing logic.

Below is the implementation of SmartFarmAdaptation. The code includes only one Python code block as requested.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0
    LOCK_STEPS = 2         # steps a drone must persist in commanded group to be considered locked
    MAX_STEAL_FRACTION = 0.25  # fraction of protecting drones allowed to be reassigned for top field

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # last commanded group per component id (for persistence/hysteresis)
        self.prev_assigned = {}
        # number of consecutive steps observed matching prev_assigned
        self.streak = {}

    def _dist(self, loc, pt):
        dx = (loc.x if hasattr(loc, "x") else loc[0]) - pt[0]
        dy = (loc.y if hasattr(loc, "y") else loc[1]) - pt[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protect_group(fid):
            return f"protecting {fid}"

        comp_by_id = {id(c): c for c in components}
        total_drones = len(components)
        half_needed = (total_drones + 1) // 2

        # Observed group for each drone (based on state & target)
        observed = {}
        for c in components:
            cid = id(c)
            if c.state in ("protecting", "moving_to_field") and c.target_id:
                observed[cid] = protect_group(c.target_id)
            else:
                observed[cid] = "idle"

        # Update streak (persistence)
        for c in components:
            cid = id(c)
            last = self.prev_assigned.get(cid)
            if last is not None and last == observed.get(cid):
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0

        # Locked drones: commanded previously and persisted observed for LOCK_STEPS
        locked = {cid for cid, s in self.streak.items() if s >= self.LOCK_STEPS and self.prev_assigned.get(cid) == observed.get(cid)}

        # Fields with positive threat, sorted by threat desc
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id = {f.id: f for f in fields}

        # Precompute centers for fields
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}

        # Observed protecting drones per field
        current_protecting = {f.id: [] for f in fields}
        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id in current_protecting:
                current_protecting[c.target_id].append(cid)

        # Start planned assignments by preserving protecting drones for fully-protected fields (keep locked first, then closest)
        planned = {}
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            cur = list(current_protecting.get(fid, []))
            if req > 0 and len(cur) >= req:
                locked_here = [cid for cid in cur if cid in locked]
                unlocked_here = [cid for cid in cur if cid not in locked]
                locked_here.sort(key=lambda cid: self._dist(comp_by_id[cid].location, centers[fid]))
                unlocked_here.sort(key=lambda cid: self._dist(comp_by_id[cid].location, centers[fid]))
                keep = []
                keep.extend(locked_here)
                if len(keep) < req:
                    keep.extend(unlocked_here[: (req - len(keep)) ])
                for cid in keep[:req]:
                    planned[cid] = protect_group(fid)

        # Free pool: drones not yet planned
        free = set(id(c) for c in components) - set(planned.keys())

        # Helper: arrival time of drone cid to field fid center (0 if already protecting fid)
        def arrival_time(cid, fid):
            comp = comp_by_id[cid]
            center = centers[fid]
            if comp.state == "protecting" and comp.target_id == fid:
                return 0.0
            return self._dist(comp.location, center) / self.DRONE_SPEED

        # Choose k drones for a field preferring (in order): protecting this field, moving to it, free drones, protecting others (only if allowed)
        def choose_k_for_field(fid, k, allow_steal=False, steal_budget=0):
            cand = []
            for c in components:
                cid = id(c)
                # skip those already planned to other fields
                if cid in planned and planned[cid] != protect_group(fid):
                    continue
                comp = comp_by_id[cid]
                if comp.state == "protecting" and comp.target_id == fid:
                    tag = 0
                elif comp.state == "moving_to_field" and comp.target_id == fid:
                    tag = 1
                elif cid in free:
                    tag = 2
                else:
                    tag = 3
                # don't consider locked protecting drones as steal candidates
                if tag == 3 and cid in locked:
                    continue
                t = arrival_time(cid, fid)
                cand.append((tag, t, cid))
            cand.sort(key=lambda x: (x[0], x[1]))
            chosen = []
            steals_used = 0
            for tag, t, cid in cand:
                if len(chosen) >= k:
                    break
                if tag == 3:
                    if not allow_steal or steals_used >= steal_budget:
                        continue
                    # ensure we don't steal from equal-or-higher threat fields
                    comp = comp_by_id[cid]
                    src = comp.target_id
                    if src in field_by_id and field_by_id[src].threat_level >= field_by_id[fid].threat_level:
                        continue
                    steals_used += 1
                chosen.append(cid)
            return chosen

        # Compute overall steal budget for reassignment (for top field only)
        total_current_protecting = sum(len(current_protecting.get(f.id, [])) for f in fields)
        max_steal = max(1, int(math.ceil(total_current_protecting * self.MAX_STEAL_FRACTION)))

        # 1) Always fully protect the most threatened field using the fastest arrivals (respecting locked drones)
        if fields:
            top = fields[0]
            top_id = top.id
            top_req = getattr(top, "drones_for_full_protection", 0)
            already_top = sum(1 for cid, grp in planned.items() if grp == protect_group(top_id))
            need_top = max(0, top_req - already_top)
            if need_top > 0:
                # Prefer not to steal; allow limited stealing only if necessary
                chosen = choose_k_for_field(top_id, need_top, allow_steal=True, steal_budget=max_steal)
                for cid in chosen:
                    planned[cid] = protect_group(top_id)
                    free.discard(cid)
                    # if we used a protecting drone from another field, try to remove it from that field's list
                    comp = comp_by_id[cid]
                    if comp.state == "protecting" and comp.target_id in current_protecting and cid in current_protecting[comp.target_id]:
                        try:
                            current_protecting[comp.target_id].remove(cid)
                        except ValueError:
                            pass

        # 2) For remaining fields, greedily full-protect using only free drones (avoid stealing)
        remaining_fields = [f for f in fields if not (fields and f.id == fields[0].id)]
        # Sort by benefit = threat / drones_needed (prefer small required, high threat)
        remaining_fields.sort(key=lambda f: (f.threat_level / max(1, getattr(f, "drones_for_full_protection", 1))), reverse=True)
        for f in remaining_fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
            need = max(0, req - already)
            if need <= 0:
                continue
            # pick nearest free drones by arrival time
            free_list = [(arrival_time(cid, fid), cid) for cid in free]
            free_list.sort(key=lambda x: x[0])
            for _, cid in free_list[:need]:
                planned[cid] = protect_group(fid)
                free.discard(cid)

        # 3) Softly satisfy the "half used" guideline by assigning remaining free drones to highest-benefit fields (partial allowed)
        assigned_count = sum(1 for cid, grp in planned.items() if grp != "idle")
        if assigned_count < half_needed and free:
            remaining = half_needed - assigned_count
            # fields sorted by threat desc
            for f in fields:
                if remaining <= 0:
                    break
                fid = f.id
                req = getattr(f, "drones_for_full_protection", 0)
                already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
                space = max(0, req - already)
                if space <= 0:
                    continue
                free_list = [(arrival_time(cid, fid), cid) for cid in free]
                free_list.sort(key=lambda x: x[0])
                take = min(space, remaining, len(free_list))
                for _, cid in free_list[:take]:
                    planned[cid] = protect_group(fid)
                    free.discard(cid)
                    remaining -= 1

        # 4) Any remaining unplanned drones -> idle
        for c in components:
            cid = id(c)
            if cid not in planned:
                planned[cid] = "idle"

        # 5) Trim overprotection (keep locked then closest)
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            assigned = [cid for cid, grp in planned.items() if grp == protect_group(fid)]
            if len(assigned) <= req:
                continue
            locked_assigned = [cid for cid in assigned if cid in locked]
            unlocked_assigned = [cid for cid in assigned if cid not in locked]
            unlocked_assigned.sort(key=lambda cid: arrival_time(cid, fid))
            keep = locked_assigned[:req]
            if len(keep) < req:
                need_more = req - len(keep)
                keep.extend(unlocked_assigned[:need_more])
            drop = set(assigned) - set(keep)
            for cid in drop:
                planned[cid] = "idle"

        # 6) Finally apply assignments (validate group ids) and update persistence tracking
        for c in components:
            cid = id(c)
            group = planned.get(cid, "idle")
            if group not in group_ids:
                group = "idle"
            environment.assign_group(c, group)
            last = self.prev_assigned.get(cid)
            self.prev_assigned[cid] = group
            if last == group:
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0