from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0
    PERSIST_LOCK_STEPS = 2  # steps the commanded group must persist before drone is locked

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track previously commanded group per drone (by id)
        self.prev_assigned = {}
        # streak: consecutive steps observed matching prev_assigned
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

        # Observed group (based on state and target)
        observed = {}
        for c in components:
            cid = id(c)
            if c.state in ("protecting", "moving_to_field") and c.target_id:
                observed[cid] = protect_group(c.target_id)
            else:
                observed[cid] = "idle"

        # Update streaks (how long commanded group matched observed)
        for c in components:
            cid = id(c)
            last = self.prev_assigned.get(cid)
            if last is not None and last == observed.get(cid):
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0

        # Locked drones: commanded previously and persisted
        locked = {cid for cid, s in self.streak.items() if s >= self.PERSIST_LOCK_STEPS and self.prev_assigned.get(cid) == observed.get(cid)}

        # Fields with positive threat, sorted by descending threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id = {f.id: f for f in fields}

        # Precompute centers
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}

        # Observed protecting drones per field
        current_protecting = {f.id: [] for f in fields}
        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id in current_protecting:
                current_protecting[c.target_id].append(cid)

        # Start planned assignments by preserving observed protecting drones (stability)
        planned = {}
        for f in fields:
            for cid in current_protecting.get(f.id, []):
                planned[cid] = protect_group(f.id)

        # Free pool: drones not planned yet
        free = set(id(c) for c in components) - set(planned.keys())

        # Trim overprotection observed: if a field has more protectors than required, keep locked first, then closest
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            cur = list(current_protecting.get(fid, []))
            if len(cur) <= req:
                continue
            # Partition locked and unlocked
            locked_in_field = [cid for cid in cur if cid in locked]
            unlocked = [cid for cid in cur if cid not in locked]
            keep = []
            # keep locked first up to req
            if locked_in_field:
                # sort locked by distance to center to prefer closest locked if too many locked
                locked_in_field.sort(key=lambda cid: self._dist(comp_by_id[cid].location, centers[fid]))
                keep.extend(locked_in_field[:req])
            # if space remains, keep closest unlocked
            space = req - len(keep)
            if space > 0 and unlocked:
                unlocked.sort(key=lambda cid: self._dist(comp_by_id[cid].location, centers[fid]))
                keep.extend(unlocked[:space])
            # drones to release:
            to_release = set(cur) - set(keep)
            for cid in to_release:
                # remove from planned and add to free
                planned.pop(cid, None)
                free.add(cid)

        # Helper: arrival time to a field center
        def arrival_time(cid, fid):
            comp = comp_by_id[cid]
            center = centers[fid]
            # if already protecting that field, treat arrival as 0
            if comp.state == "protecting" and comp.target_id == fid:
                return 0.0
            return self._dist(comp.location, center) / self.DRONE_SPEED

        # Helper: build candidate list for a field sorted by preference and arrival time
        # preference tag: 0 = protecting this field, 1 = moving_to_field to this field, 2 = free (idle/moving elsewhere), 3 = protecting other field
        def candidates_for_field(fid):
            cand = []
            for c in components:
                cid = id(c)
                # if already planned to protect this field, include as top priority
                if planned.get(cid) == protect_group(fid):
                    tag = 0
                    t = 0.0
                else:
                    comp = comp_by_id[cid]
                    if comp.state == "moving_to_field" and comp.target_id == fid:
                        tag = 1
                    elif cid in free:
                        tag = 2
                    else:
                        tag = 3
                    t = arrival_time(cid, fid)
                # exclude locked protecting drones for stealing (unless they already protect this field -> tag 0)
                if tag == 3 and cid in locked:
                    continue
                cand.append((tag, t, cid))
            # sort by (tag, arrival_time)
            cand.sort(key=lambda x: (x[0], x[1]))
            return cand

        # Assign to top-threat field first
        if fields:
            top = fields[0]
            top_id = top.id
            req_top = getattr(top, "drones_for_full_protection", 0)
            # count already planned for top
            already_top = sum(1 for cid, grp in planned.items() if grp == protect_group(top_id))
            need_top = max(0, req_top - already_top)
            if need_top > 0:
                cand = candidates_for_field(top_id)
                # pick candidates in order, but avoid taking locked protecting drones from other fields (filtered)
                picked = []
                for tag, t, cid in cand:
                    if cid in planned and planned[cid] == protect_group(top_id):
                        continue  # already counted
                    # prefer not to steal: accept tag 2 or 1 first; tag 3 only if necessary
                    if tag == 3:
                        # only accept tag 3 if not enough other candidates remain
                        # check how many non-tag3 candidates are available after this point
                        # simpler rule: permit tag 3 only if number of non-tag3 candidates < need_top
                        non_tag3_left = sum(1 for (tg, _, _) in cand if tg != 3)
                        # if there are enough non-tag3, skip this tag3 until later
                        if non_tag3_left >= need_top and tag == 3:
                            continue
                    picked.append(cid)
                    if cid in free:
                        free.discard(cid)
                    need_top -= 1
                    if need_top <= 0:
                        break
                # assign picked to top
                for cid in picked:
                    planned[cid] = protect_group(top_id)

        # After top field, try to fully protect subsequent fields only using free (no stealing)
        for f in fields[1:]:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
            need = max(0, req - already)
            if need <= 0:
                continue
            # gather free candidates sorted by arrival
            free_cands = []
            for cid in list(free):
                free_cands.append((arrival_time(cid, fid), cid))
            free_cands.sort(key=lambda x: x[0])
            for t, cid in free_cands[:need]:
                planned[cid] = protect_group(fid)
                free.discard(cid)

        # If after full protections fewer than half of drones are protecting, assign additional free drones (no stealing) to highest-threat fields
        assigned_count = sum(1 for cid, grp in planned.items() if grp != "idle")
        if assigned_count < half_needed:
            remaining = half_needed - assigned_count
            for f in fields:
                if remaining <= 0:
                    break
                fid = f.id
                req = getattr(f, "drones_for_full_protection", 0)
                already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
                space = max(0, req - already)
                if space <= 0:
                    continue
                # pick up to min(space, remaining) from free closest
                free_cands = []
                for cid in list(free):
                    free_cands.append((arrival_time(cid, fid), cid))
                free_cands.sort(key=lambda x: x[0])
                for t, cid in free_cands[:min(space, remaining)]:
                    planned[cid] = protect_group(fid)
                    free.discard(cid)
                    remaining -= 1
                    if remaining <= 0:
                        break

        # Any still-unplanned drones -> idle
        for c in components:
            cid = id(c)
            if cid not in planned:
                planned[cid] = "idle"

        # Ensure no field is overprotected: trim to drones_for_full_protection keeping locked and then closest
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            assigned = [cid for cid, grp in planned.items() if grp == protect_group(fid)]
            if len(assigned) <= req:
                continue
            # sort assigned: locked first (keep them), then by arrival time
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

        # Apply assignments via environment.assign_group, validating group names
        for c in components:
            cid = id(c)
            group = planned.get(cid, "idle")
            if group not in group_ids:
                group = "idle"
            environment.assign_group(c, group)
            # update prev_assigned and streak for next step
            last = self.prev_assigned.get(cid)
            self.prev_assigned[cid] = group
            if last == group:
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0