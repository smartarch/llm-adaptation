Reasoning and improved adaptation strategy

What I changed and why
- Use a utility-driven greedy allocation that explicitly considers:
  - how many extra drones are needed to fully protect a field (additional_needed),
  - the field threat level,
  - how fast drones can get there (arrival time for the k-th required drone),
  - and the cost of moving drones already protecting other fields.
- Score fields by estimated benefit-per-drone adjusted by arrival time: score = threat_level / (additional_needed * (1 + arrival_time_k)). This prefers high-threat fields that can be fully protected with few, fast-arriving drones.
- Prefer drones that are already protecting the same field or are already moving to it; prefer idle/moving drones over stealing protecting drones. Only steal protecting drones as a last resort, and do not steal from fields that are more threatened than the target.
- Stronger persistence: treat drones as "locked" if we commanded them to their current observed group previously and they have persisted for >= 2 steps — avoid moving them unless absolutely necessary.
- Limit reassignments from protecting drones conservatively (20% of currently protecting drones) to reduce oscillation.
- After greedily fully protecting the best-scoring fields, only perform partial assignments to meet the "at least half drones used" guideline if necessary — and even then pick the least disruptive candidates (idle/moving first).
- Trim any overprotection (never assign more than drones_for_full_protection to a field).
- Overall goal: concentrate resources to fully protect the most valuable/feasible fields, minimize wasted travel, and keep assignments stable across steps.

The code below implements this strategy in the SmartFarmAdaptation class.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0  # units per time step

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # last commanded group per component id
        self.prev_assigned = {}
        # consecutive steps the same command was observed
        self.streak = {}

    def _distance(self, loc, point):
        dx = (loc.x if hasattr(loc, "x") else loc[0]) - point[0]
        dy = (loc.y if hasattr(loc, "y") else loc[1]) - point[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protect_group(fid):
            return f"protecting {fid}"

        comp_by_id = {id(c): c for c in components}
        total_drones = len(components)

        # Observed group based on state and target
        observed_group = {}
        for c in components:
            if c.state in ("protecting", "moving_to_field") and c.target_id:
                observed_group[id(c)] = protect_group(c.target_id)
            else:
                observed_group[id(c)] = "idle"

        # Update streak counters based on previous command and observed group
        for c in components:
            cid = id(c)
            last_cmd = self.prev_assigned.get(cid)
            if last_cmd is not None and last_cmd == observed_group.get(cid):
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0

        # Candidate fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # map field id -> field object and threat
        field_by_id = {f.id: f for f in fields}
        # Precompute centers
        centers = {}
        for f in fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Current protecting drones per field
        current_protecting = {f.id: [] for f in fields}
        protecting_set = set()
        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id in current_protecting:
                current_protecting[c.target_id].append(cid)
                protecting_set.add(cid)

        # Locked drones: commanded previously to same observed group and persisted for >=2 steps
        locked = set()
        for c in components:
            cid = id(c)
            if self.prev_assigned.get(cid) == observed_group.get(cid) and self.streak.get(cid, 0) >= 2:
                locked.add(cid)

        num_currently_protecting = len(protecting_set)
        # Allow at most 20% of protecting drones to be reassigned in one step (minimum 1)
        max_reassign_from_protecting = max(1, int(math.ceil(num_currently_protecting * 0.2)))

        # planned assignments (cid -> group)
        planned = {}
        # Initially keep all currently protecting drones assigned to their observed protecting group (stability)
        for c in components:
            cid = id(c)
            if c.state == "protecting" and c.target_id:
                grp = protect_group(c.target_id)
                planned[cid] = grp

        free_components = set(id(c) for c in components) - set(planned.keys())

        # Helper: arrival time for a component to field center (0 if already protecting that field)
        def arrival_time(cid, field_center, field_id=None):
            comp = comp_by_id[cid]
            # If currently protecting this field, arrival time = 0 (already there)
            if comp.state == "protecting" and comp.target_id == field_id:
                return 0.0
            # Otherwise, compute distance / speed
            dist = self._distance(comp.location, field_center)
            return dist / self.DRONE_SPEED

        # Helper: produce candidate list for a field (excluding locked protecting drones that shouldn't be moved)
        # Each entry: (tag, arrival_time, cid, source_field_id_or_None)
        # tag priorities: 0 = already protecting this field, 1 = moving_to_field toward it, 2 = idle/moving elsewhere, 3 = protecting other field
        def candidate_list_for_field(field_id):
            center = centers[field_id]
            lst = []
            for c in components:
                cid = id(c)
                comp = comp_by_id[cid]
                # If we already planned this drone elsewhere (explicitly kept), skip here
                if cid in planned and planned[cid] != protect_group(field_id):
                    continue
                # Tag
                if comp.state == "protecting" and comp.target_id == field_id:
                    tag = 0
                    src = field_id
                elif comp.state == "moving_to_field" and comp.target_id == field_id:
                    tag = 1
                    src = comp.target_id
                elif cid in protecting_set:
                    tag = 3
                    src = comp.target_id if comp.target_id else None
                else:
                    tag = 2
                    src = None
                # If locked and it's protecting another field, exclude from candidates
                if cid in locked and tag == 3:
                    continue
                # compute arrival time
                t = arrival_time(cid, center, field_id)
                lst.append((tag, t, cid, src))
            # sort by tag then arrival time (prefer 0,1,2 over 3)
            lst.sort(key=lambda x: (x[0], x[1]))
            return lst

        # For each field compute additional_needed and estimate arrival_time_k for k required drones
        field_scores = []
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            currently = len(current_protecting.get(fid, []))
            additional_needed = max(0, req - currently)
            if additional_needed == 0:
                # Already fully protected, give it a high score to keep it protected
                score = float('inf')
                est_arrival_k = 0.0
            else:
                cand = candidate_list_for_field(fid)
                # compute the arrival time of the k-th candidate if available
                if len(cand) < additional_needed:
                    est_arrival_k = float('inf')
                else:
                    est_arrival_k = cand[additional_needed - 1][1]
                # score: threat / (additional_needed * (1 + est_arrival_k)), so fewer drones needed and faster arrival increases score
                if est_arrival_k == float('inf'):
                    score = 0.0
                else:
                    score = (getattr(f, "threat_level", 0.0)) / (max(1, additional_needed) * (1.0 + est_arrival_k))
            field_scores.append((score, f))

        # Sort fields by descending score (more urgent/efficient first)
        field_scores.sort(key=lambda x: x[0], reverse=True)

        # Keep track of how many protecting drones we have taken from other fields
        protecting_moved = 0

        # Greedy allocation: try to fully protect fields in score order
        for score, f in field_scores:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            currently_planned = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
            need = max(0, req - currently_planned)
            if need <= 0:
                continue
            # get candidates
            cand = candidate_list_for_field(fid)
            for tag, t, cid, src in cand:
                if need <= 0:
                    break
                if cid in planned and planned[cid] == protect_group(fid):
                    continue
                # If candidate is protecting another field (tag==3), be cautious:
                if tag == 3:
                    # don't steal from fields that are more threatened than this one
                    src_threat = field_by_id.get(src, None).threat_level if src in field_by_id else 0.0
                    if src_threat >= f.threat_level:
                        continue
                    # check move budget
                    if protecting_moved >= max_reassign_from_protecting:
                        continue
                    # do not move locked protecting drones (should have been filtered earlier)
                    if cid in locked:
                        continue
                    protecting_moved += 1
                # assign this drone to protect this field
                planned[cid] = protect_group(fid)
                # if it was previously marked in free_components, remove
                free_components.discard(cid)
                need -= 1

        # After greedy full protections, count assigned protection
        assigned_protection = [cid for cid, grp in planned.items() if grp != "idle"]
        half_needed = (total_drones + 1) // 2

        # If fewer than half used, do partial assignment but pick minimal, least-disruptive additions
        if len(assigned_protection) < half_needed:
            # pick the best field to add partial drones to: highest threat, quickest candidates, but avoid stealing from higher-threat fields
            # build candidate lists for each field again and pick drones until half reached
            remaining_needed = half_needed - len(assigned_protection)
            # sort fields by threat descending (prefer higher threat for partial)
            partial_fields = sorted(fields, key=lambda x: x.threat_level, reverse=True)
            for f in partial_fields:
                if remaining_needed <= 0:
                    break
                fid = f.id
                # compute how many we could add without exceeding req
                req = getattr(f, "drones_for_full_protection", 0)
                already = sum(1 for cid, grp in planned.items() if grp == protect_group(fid))
                space = max(0, req - already)
                if space <= 0:
                    continue
                # candidate list prioritizing non-protecting drones
                cand = candidate_list_for_field(fid)
                for tag, t, cid, src in cand:
                    if remaining_needed <= 0 or space <= 0:
                        break
                    if cid in planned and planned[cid] == protect_group(fid):
                        continue
                    if tag == 3:
                        src_threat = field_by_id.get(src, None).threat_level if src in field_by_id else 0.0
                        if src_threat >= f.threat_level:
                            continue
                        if protecting_moved >= max_reassign_from_protecting:
                            continue
                        if cid in locked:
                            continue
                        protecting_moved += 1
                    planned[cid] = protect_group(fid)
                    free_components.discard(cid)
                    remaining_needed -= 1
                    space -= 1

        # Any still-unplanned drones -> idle
        for c in components:
            cid = id(c)
            if cid not in planned:
                planned[cid] = "idle"

        # Trim any overprotection (keep closest req drones for each field)
        for f in fields:
            fid = f.id
            req = getattr(f, "drones_for_full_protection", 0)
            assigned_cids = [cid for cid, grp in planned.items() if grp == protect_group(fid)]
            if len(assigned_cids) <= req:
                continue
            # sort by arrival time and keep closest req
            center = centers[fid]
            assigned_cids.sort(key=lambda cid: arrival_time(cid, center, fid))
            keep = set(assigned_cids[:req])
            for cid in assigned_cids[req:]:
                planned[cid] = "idle"

        # Final assignment via environment.assign_group
        for c in components:
            cid = id(c)
            group = planned.get(cid, "idle")
            # ensure group is valid
            if group not in group_ids:
                group = "idle"
            environment.assign_group(c, group)
            # update prev_assigned & streak
            last = self.prev_assigned.get(cid)
            self.prev_assigned[cid] = group
            if last == group:
                self.streak[cid] = self.streak.get(cid, 0) + 1
            else:
                self.streak[cid] = 0
```