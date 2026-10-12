Reasoning and adaptation strategy

Observations from previous runs:
- Aggressive stealing and oscillatory reassignment increased travel and damage.
- Arrival time (distance / speed) is a much better proxy than raw distance.
- Stability (persistence) matters: keep drones where they are when appropriate to avoid wasted travel.
- Full protection of a high-threat field is more valuable than partially protecting many fields.
- Use idle/moving drones first to fill protection needs; steal protecting drones only sparingly for the top field and only from lower-threat fields.

Strategy implemented here:
1. Compute field centers and arrival times for every drone -> arrival_time = distance / 2.0 (drone speed = 2).
2. Treat a drone as "locked" if we commanded it to the same group in prior step and the observed state matched for 2 or more steps; locked drones are strongly disfavored for reassignment.
3. Always ensure the single highest-threat field is fully protected first:
   - Keep protecting drones already on that field (trim extras to the closest required, releasing others).
   - Fill remaining slots using the fastest-available drones: prefer (in order) already protecting this field, moving-to-this-field, free drones (idle/moving), and only if necessary (and limited) protecting drones from lower-threat fields.
   - Cap the number of protecting drones we reassign in one step (conservative fraction).
4. After the top field is secured, try to fully protect other fields greedily using only free drones (no stealing). This concentrates resources on fully protecting fields rather than many partials.
5. If fewer than half of drones are protecting after full allocations, assign additional free drones to the highest-threat fields (partial allowed) to reach the half threshold (no stealing).
6. Never overprotect a field (trim to drones_for_full_protection, preferring locked and closest).
7. Explicitly assign every drone each step using environment.assign_group(component, group_id). Track prev_assigned and streak for persistence.

This approach keeps the decision simple and stable, prioritizes the most important field, uses arrival time to choose the best drones, and minimizes disruptive stealing. The implementation below follows the required class signature and uses only one Python code block.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0
    LOCK_STEPS = 2        # steps a commanded assignment must persist to be treated as locked
    STEAL_FRACTION = 0.25 # fraction of protecting drones we may reassign when absolutely necessary

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # last commanded group per drone id
        self.prev_assigned = {}
        # how many consecutive steps the drone was observed matching prev_assigned
        self.streak = {}

    def _dist(self, loc, pt):
        dx = (loc.x if hasattr(loc, "x") else loc[0]) - pt[0]
        dy = (loc.y if hasattr(loc, "y") else loc[1]) - pt[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protect_group(fid):
            return f"protecting {fid}"

        comp_by_id = {id(c): c for c in components}
        total = len(components)
        half_needed = (total + 1) // 2

        # Observed group based on drone state
        observed = {}
        for c in components:
            cid = id(c)
            if c.state in ("protecting", "moving_to_field") and c.target_id:
                observed[cid] = protect_group(c.target_id)
            else:
                observed[cid] = "idle"

        # Update streak (persistence) counters
        for c in components:
            cid = id(c)
            last = self.prev_assigned.get(cid)
            if last is not None and last == observed.get(cid):
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0

        # Locked drones: commanded previously and observed same for LOCK_STEPS
        locked = {cid for cid, s in self.streak.items() if s >= self.LOCK_STEPS and self.prev_assigned.get(cid) == observed.get(cid)}

        # Filter fields with threat > 0 and sort by descending threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id = {f.id: f for f in fields}

        # Compute field centers
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in fields}

        # Observed protecting drones per field
        current_protecting = {f.id: [] for f in fields}
        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id in current_protecting:
                current_protecting[c.target_id].append(cid)

        # Helper: arrival time to field center
        def arrival_time(cid, fid):
            comp = comp_by_id[cid]
            if comp.state == "protecting" and comp.target_id == fid:
                return 0.0
            center = centers[fid]
            return self._dist(comp.location, center) / self.DRONE_SPEED

        # Start planned assignments by preserving protecting drones for fully-protected fields (keep locked first then closest)
        planned = {}
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            cur = list(current_protecting.get(fid, []))
            if req > 0 and len(cur) >= req:
                locked_here = [cid for cid in cur if cid in locked]
                unlocked_here = [cid for cid in cur if cid not in locked]
                locked_here.sort(key=lambda cid: arrival_time(cid, fid))
                unlocked_here.sort(key=lambda cid: arrival_time(cid, fid))
                keep = locked_here[:req]
                if len(keep) < req:
                    need_more = req - len(keep)
                    keep.extend(unlocked_here[:need_more])
                for cid in keep[:req]:
                    planned[cid] = protect_group(fid)

        # Free drones are those not yet planned
        free = set(id(c) for c in components) - set(planned.keys())

        # If no fields, assign all to idle
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
                cid = id(c)
                last = self.prev_assigned.get(cid)
                self.prev_assigned[cid] = "idle"
                if last == "idle":
                    self.streak[cid] = self.streak.get(cid, 0) + 1
                else:
                    self.streak[cid] = 0
            return

        # Compute steal budget based on how many protecting drones exist
        total_protecting = sum(len(current_protecting.get(f.id, [])) for f in fields)
        max_steal = max(1, int(math.ceil(total_protecting * self.STEAL_FRACTION))) if total_protecting > 0 else 0

        # Function to pick k drones for a field: prefer protecting-this (tag 0), moving-to (1), free (2), protecting-other (3)
        def pick_for_field(fid, k, allow_steal=False, steal_budget=0):
            candidates = []
            for c in components:
                cid = id(c)
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
                candidates.append((tag, t, cid, comp))
            candidates.sort(key=lambda x: (x[0], x[1]))
            chosen = []
            steals = 0
            for tag, t, cid, comp in candidates:
                if len(chosen) >= k:
                    break
                if tag == 3:
                    if not allow_steal or steals >= steal_budget:
                        continue
                    src = comp.target_id
                    if src in field_by_id and field_by_id[src].threat_level >= field_by_id[fid].threat_level:
                        continue
                    steals += 1
                chosen.append(cid)
            return chosen

        # 1) Fully protect top-threat field with fastest arrivals; allow limited stealing only if necessary
        top = fields[0]
        top_id = top.id
        top_req = getattr(top, "drones_for_full_protection", 0)
        if top_req > 0:
            already_top = sum(1 for cid, grp in planned.items() if grp == protect_group(top_id))
            need_top = max(0, top_req - already_top)
            if need_top > 0:
                chosen = pick_for_field(top_id, need_top, allow_steal=True, steal_budget=max_steal)
                for cid in chosen:
                    planned[cid] = protect_group(top_id)
                    free.discard(cid)
                    # If this drone was protecting another field, remove from that list to avoid double-count
                    comp = comp_by_id[cid]
                    if comp.state == "protecting" and comp.target_id in current_protecting and cid in current_protecting[comp.target_id]:
                        try:
                            current_protecting[comp.target_id].remove(cid)
                        except ValueError:
                            pass

        # 2) For other fields, attempt to fully protect using only free drones (no stealing)
        for f in fields[1:]:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
            need = max(0, req - already)
            if need <= 0:
                continue
            free_list = [(arrival_time(cid, fid), cid) for cid in free]
            free_list.sort(key=lambda x: x[0])
            for _, cid in free_list[:need]:
                planned[cid] = protect_group(fid)
                free.discard(cid)

        # 3) If fewer than half the drones are protecting, assign free drones to highest-threat fields (partial allowed) until half reached
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
                # choose closest free drones
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

        # 5) Trim any overprotection: for each field keep locked drones first then closest up to required
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

        # 6) Apply assignments, validating group ids, and update prev_assigned & streak
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
```