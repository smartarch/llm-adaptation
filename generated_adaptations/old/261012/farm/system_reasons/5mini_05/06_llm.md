Strategy and reasoning

Improvements over the previous implementation to reduce damage:
- Account for travel time explicitly: drones move at speed 2, so travel_time = distance / 2. Fields that can be reached quickly by enough drones get priority because protection becomes effective earlier.
- Always fully protect the top-threat field (functional requirement). Keep drones already protecting it when reasonable to preserve stability.
- Score other fields by a value-per-drone metric that incorporates threat_level, drones_required, and average arrival time for the needed drones. This favors high-threat, low-cost (in drones/time) fields.
- Greedy selection of additional fields to fully protect until we satisfy the "at least half of drones protecting" target, preferring fields with the best score.
- When selecting individual drones for a field, prefer: (1) drones already protecting that field, (2) drones moving to it, (3) idle drones, then others. Break ties by shorter travel time and lower stability cost (preferring to move low-stay drones).
- Avoid overprotection by trimming assigned drones to the required count using stability-aware tie-breakers (prefer keeping drones with higher stay counters).
- Maintain per-drone bookkeeping (prev assignment and stay counters) to reduce churn and meet the stability requirement.

Below is the Python implementation of this adaptation strategy. It contains one class SmartFarmAdaptation derived from FarmAdaptation and implements assign_drones() accordingly.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict
import heapq
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track previous assignments per drone (by id)
        self.prev_assignments = {}
        # How many consecutive steps the drone stayed in same group
        self.stay_counters = defaultdict(int)
        # drone speed (given)
        self.drone_speed = 2.0

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, loc, center):
        dx = loc.x - center[0]
        dy = loc.y - center[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        components = list(components)
        total_drones = len(components)
        min_protectors_target = math.ceil(total_drones / 2)

        # Convenience
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # Prepare fields and centers
        fields = list(environment.fields)
        field_centers = {f.id: self._field_center(f) for f in fields}
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all to idle
        if not threatened_fields:
            for c in components:
                target = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, target)
                cid = id(c)
                if self.prev_assignments.get(cid) == target:
                    self.stay_counters[cid] += 1
                else:
                    self.stay_counters[cid] = 1
                self.prev_assignments[cid] = target
            return

        # Build component metadata: distances and travel times to each field
        comp_meta = {}
        for c in components:
            cid = id(c)
            dist_map = {}
            travel_map = {}
            for f in fields:
                center = field_centers[f.id]
                d = self._dist(c.location, center)
                dist_map[f.id] = d
                travel_map[f.id] = d / self.drone_speed
            comp_meta[cid] = {
                "comp": c,
                "state": getattr(c, "state", None),
                "target_id": getattr(c, "target_id", None),
                "prev_group": self.prev_assignments.get(cid),
                "stay": self.stay_counters.get(cid, 0),
                "dist": dist_map,
                "travel": travel_map
            }

        # Pick primary field (highest threat)
        primary_field = max(threatened_fields, key=lambda f: f.threat_level)
        primary_gid = protecting_group(primary_field.id)
        primary_required = int(getattr(primary_field, "drones_for_full_protection", 0))
        if primary_gid not in group_ids:
            primary_required = 0

        assigned_for_field = defaultdict(list)
        available_cids = set(comp_meta.keys())

        # Helper: pick up to k best available drones for a field, preferring current protectors and low-stay movers
        def pick_k_for_field(field_id, k):
            candidates = []
            for cid in list(available_cids):
                m = comp_meta[cid]
                # priority: 0 current protector for field, 1 prev_group protecting field, 2 moving to field, 3 idle, 4 others
                if m["state"] == "protecting" and m["target_id"] == field_id:
                    pri = 0
                elif m["prev_group"] == protecting_group(field_id):
                    pri = 1
                elif m["target_id"] == field_id:
                    pri = 2
                elif m["state"] == "idle":
                    pri = 3
                else:
                    pri = 4
                # tie-break by travel time then stay (prefer low stay to move)
                candidates.append( (pri, m["travel"].get(field_id, float('inf')), m["stay"], cid) )
            candidates.sort(key=lambda x: (x[0], x[1], x[2]))
            picks = []
            for item in candidates[:k]:
                cid = item[3]
                picks.append(comp_meta[cid]["comp"])
            return picks

        # 1) Secure primary field: keep existing protectors up to required, then add closest (by travel/stay)
        current_protectors = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == primary_field.id]
        # If too many current protectors, trim by stay (keep high-stay)
        if len(current_protectors) > primary_required:
            current_protectors.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(primary_field.id, 0)))
            current_protectors = current_protectors[:primary_required]
        # Reserve and assign them
        for cid in current_protectors:
            assigned_for_field[primary_field.id].append(comp_meta[cid]["comp"])
            if cid in available_cids:
                available_cids.remove(cid)
        need = max(0, primary_required - len(assigned_for_field[primary_field.id]))
        if need > 0:
            picks = pick_k_for_field(primary_field.id, need)
            for comp in picks:
                cid = id(comp)
                if cid in available_cids:
                    assigned_for_field[primary_field.id].append(comp)
                    available_cids.remove(cid)

        # 2) Score other fields for greedy selection (value per drone adjusted by arrival time)
        other_fields = [f for f in threatened_fields if f.id != primary_field.id]
        field_scores = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            # compute travel times of available drones
            travel_times = [comp_meta[cid]["travel"].get(f.id, float('inf')) for cid in available_cids]
            travel_times.sort()
            # account for already protecting drones for that field
            already_prot_cids = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == f.id]
            already = min(len(already_prot_cids), req)
            need_new = max(0, req - already)
            if need_new == 0:
                avg_time = 0.0
            elif len(travel_times) >= need_new:
                avg_time = sum(travel_times[:need_new]) / need_new
            else:
                # not enough free drones to reach k quickly; set low score
                avg_time = float('inf')
            if math.isfinite(avg_time):
                score = f.threat_level / (req * (1.0 + avg_time))
            else:
                score = 0.0
            field_scores.append((score, f, need_new, req, avg_time))
        # sort by score desc, tie break by threat_level
        field_scores.sort(key=lambda x: (-x[0], -x[1].threat_level))

        # 3) Greedily choose fields to fully protect until we reach min_protectors_target or run out
        protected_count = sum(len(v) for v in assigned_for_field.values())
        chosen_fields = []
        for score, f, need_new, req, avg_time in field_scores:
            if score <= 0:
                continue
            # if we already have enough protectors, break
            if protected_count >= min_protectors_target:
                break
            # require that we can supply required drones (using available ones plus existing protectors)
            existing_cids = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == f.id]
            already = min(len(existing_cids), req)
            total_available = len(available_cids) + already
            if total_available < req:
                # not feasible without moving too many stable protectors, skip
                continue
            # choose this field
            chosen_fields.append((f, req))
            # estimate protected_count increment: we'll add req (including already)
            protected_count += req

        # 4) For chosen fields, assign drones (keep current protectors, then pick needed)
        for f, req in chosen_fields:
            fid = f.id
            # keep current protectors (prefer high-stay)
            cur = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == fid]
            # keep up to req, prefer high stay
            cur.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(fid, 0)))
            kept = cur[:req]
            for cid in kept:
                if cid in available_cids:
                    available_cids.remove(cid)
                assigned_for_field[fid].append(comp_meta[cid]["comp"])
            still_need = max(0, req - len(assigned_for_field[fid]))
            if still_need > 0:
                picks = pick_k_for_field(fid, still_need)
                for comp in picks:
                    cid = id(comp)
                    if cid in available_cids:
                        assigned_for_field[fid].append(comp)
                        available_cids.remove(cid)

        # 5) Finalize assignments, trimming any overprotection (keep best by stability and proximity)
        final_assignments = {}
        for fid, comps in assigned_for_field.items():
            fobj = next((f for f in fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # prefer keep: currently_protecting & target match (0), then higher stay, then closer
                comps_sorted = sorted(
                    comps,
                    key=lambda c: (
                        0 if (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid) else 1,
                        -self.stay_counters.get(id(c), 0),
                        self._dist(c.location, field_centers.get(fid, (0,0)))
                    )
                )
                comps = comps_sorted[:req]
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # 6) Remaining drones -> idle (or keep previous if idle not available)
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                if "idle" in group_ids:
                    final_assignments[cid] = "idle"
                else:
                    prev = self.prev_assignments.get(cid)
                    if prev in group_ids:
                        final_assignments[cid] = prev
                    elif primary_gid in group_ids and len(assigned_for_field.get(primary_field.id, [])) < primary_required:
                        final_assignments[cid] = primary_gid
                    else:
                        final_assignments[cid] = group_ids[0] if group_ids else "idle"

        # 7) Execute assignments and update stay counters
        for c in components:
            cid = id(c)
            group = final_assignments.get(cid, "idle")
            if group not in group_ids:
                group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            environment.assign_group(c, group)
            prev = self.prev_assignments.get(cid)
            if prev == group:
                self.stay_counters[cid] = self.stay_counters.get(cid, 0) + 1
            else:
                self.stay_counters[cid] = 1
            self.prev_assignments[cid] = group