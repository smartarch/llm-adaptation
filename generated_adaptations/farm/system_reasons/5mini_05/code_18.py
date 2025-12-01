from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assignments = {}
        self.stay_counters = defaultdict(int)
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

        def protecting_group(fid):
            return f"protecting {fid}"

        # Gather fields and centers
        fields = list(environment.fields)
        centers = {f.id: self._field_center(f) for f in fields}
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle everyone explicitly
        if not threatened:
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

        # Build component metadata: travel times and state info
        comp_meta = {}
        for c in components:
            cid = id(c)
            travel = {}
            dist = {}
            for f in fields:
                center = centers[f.id]
                d = self._dist(c.location, center)
                dist[f.id] = d
                travel[f.id] = d / self.drone_speed
            comp_meta[cid] = {
                "comp": c,
                "state": getattr(c, "state", None),
                "target_id": getattr(c, "target_id", None),
                "prev_group": self.prev_assignments.get(cid),
                "stay": self.stay_counters.get(cid, 0),
                "dist": dist,
                "travel": travel
            }

        assigned_for_field = defaultdict(list)
        available_cids = set(comp_meta.keys())

        # Primary: highest threat field — must be fully protected
        primary = max(threatened, key=lambda f: f.threat_level)
        primary_gid = protecting_group(primary.id)
        primary_required = int(getattr(primary, "drones_for_full_protection", 0))
        if primary_gid not in group_ids:
            primary_required = 0

        # Select primary drones: minimize time until full protection (k-th travel time)
        # Build list of candidate (cid, travel_time) using travel map; bias to keep current protectors
        def primary_sort_key(cid):
            m = comp_meta[cid]
            # bias: if already protecting primary, treat travel as very small to keep them
            if m["state"] == "protecting" and m["target_id"] == primary.id:
                bias = 0.0
            elif m["target_id"] == primary.id:
                bias = 0.5 * m["travel"].get(primary.id, float('inf'))
            else:
                bias = m["travel"].get(primary.id, float('inf'))
            # prefer lower bias and lower stay (move low-stay first)
            return (bias, m["stay"])

        sorted_by_primary = sorted(comp_meta.keys(), key=primary_sort_key)
        primary_selected = []
        for cid in sorted_by_primary:
            if len(primary_selected) >= primary_required:
                break
            primary_selected.append(cid)
        for cid in primary_selected:
            assigned_for_field[primary.id].append(comp_meta[cid]["comp"])
            available_cids.discard(cid)

        # Helper: compute best k candidate cids (and max travel) for a field using available_cids plus existing protectors
        def best_k_for_field(field, k):
            # include current protectors first (they effectively have travel 0 if already protecting)
            cur = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == field.id]
            # travel times for current protectors treat as 0 (already there)
            times = []
            chosen = []
            # Add current protectors sorted by high stay (prefer to keep)
            cur_sorted = sorted(cur, key=lambda cid: -comp_meta[cid]["stay"])
            for cid in cur_sorted:
                if cid in chosen:
                    continue
                chosen.append(cid)
                times.append(0.0)
                if len(chosen) >= k:
                    break
            if len(chosen) < k:
                # consider available_cids sorted by travel time (prefer idle/moving ones)
                candidates = []
                for cid in available_cids:
                    if cid in chosen:
                        continue
                    m = comp_meta[cid]
                    travel = m["travel"].get(field.id, float('inf'))
                    # prefer idle/moving-to-target; then lower stay
                    cat = 0 if m["state"] == "idle" else (1 if m["target_id"] == field.id else 2)
                    candidates.append((cat, travel, m["stay"], cid))
                candidates.sort(key=lambda x: (x[0], x[1], x[2]))
                for item in candidates:
                    if len(chosen) >= k:
                        break
                    cid = item[3]
                    chosen.append(cid)
                    times.append(item[1])
            # If still not enough, return None (field not feasible)
            if len(chosen) < k:
                return None, None
            # max travel is time to full protection
            max_travel = max(times)
            return chosen, max_travel

        # Score candidate fields by threat / (k * (1 + time_to_full))
        other_fields = [f for f in threatened if f.id != primary.id]
        field_candidates = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            chosen, max_travel = best_k_for_field(f, req)
            if chosen is None:
                continue
            # score balances threat, drones required and latency
            score = (f.threat_level) / (req * (1.0 + max_travel))
            field_candidates.append((score, f, req, chosen, max_travel))
        # sort descending score
        field_candidates.sort(key=lambda x: (-x[0], -x[1].threat_level))

        # Greedily assign full protections to highest-score fields
        protected_count = sum(len(v) for v in assigned_for_field.values())
        for score, f, req, chosen_cids, max_travel in field_candidates:
            if protected_count >= min_protectors_target:
                break
            # ensure chosen_cids are still available (some may have been removed by earlier picks)
            actual = []
            # keep current protectors (if any) from chosen first
            for cid in chosen_cids:
                if cid not in available_cids and not (comp_meta[cid]["state"] == "protecting" and comp_meta[cid]["target_id"] == f.id):
                    # if it's neither available nor a current protector, skip
                    continue
                actual.append(cid)
            # if actual count less than req, try to refind best_k now that pool changed
            if len(actual) < req:
                chosen_now, max_travel_now = best_k_for_field(f, req)
                if chosen_now is None:
                    continue
                # filter to those still available or current protectors
                actual = []
                for cid in chosen_now:
                    if cid in available_cids or (comp_meta[cid]["state"] == "protecting" and comp_meta[cid]["target_id"] == f.id):
                        actual.append(cid)
                if len(actual) < req:
                    continue
            # Assign these req drones
            assigned_for_field[f.id].extend([comp_meta[cid]["comp"] for cid in actual[:req]])
            for cid in actual[:req]:
                available_cids.discard(cid)
            protected_count = sum(len(v) for v in assigned_for_field.values())

        # If still below half protected, assign remaining drones (one-by-one) to best fields by quick reach
        protected_count = sum(len(v) for v in assigned_for_field.values())
        if protected_count < min_protectors_target and available_cids:
            # Build a list of remaining fields sorted by threat per drone
            rem_fields = sorted(threatened, key=lambda f: -(f.threat_level / max(1, int(getattr(f, "drones_for_full_protection", 1)))))
            # assign remaining drones to the field they can reach earliest among rem_fields
            remaining_cids = sorted(list(available_cids), key=lambda cid: comp_meta[cid]["stay"])  # prefer low-stay to move
            while protected_count < min_protectors_target and remaining_cids:
                cid = remaining_cids.pop(0)
                best_f = None
                best_t = float('inf')
                for f in rem_fields:
                    t = comp_meta[cid]["travel"].get(f.id, float('inf'))
                    if t < best_t:
                        best_t = t
                        best_f = f
                if best_f is None:
                    break
                assigned_for_field[best_f.id].append(comp_meta[cid]["comp"])
                available_cids.discard(cid)
                protected_count += 1

        # Finalize assignments: trim overprotect and create final mapping
        final_assignments = {}
        for fid, comps in assigned_for_field.items():
            fobj = next((f for f in fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # keep currently protecting & higher-stay first, then closer drones
                def keep_key(c):
                    cid = id(c)
                    state = getattr(c, "state", None)
                    target = getattr(c, "target_id", None)
                    is_current = 0 if (state == "protecting" and target == fid) else 1
                    stay_pref = -self.stay_counters.get(cid, 0)
                    dist = self._dist(c.location, centers.get(fid, (0,0)))
                    return (is_current, stay_pref, dist)
                comps_sorted = sorted(comps, key=keep_key)
                comps = comps_sorted[:req]
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # Remaining drones -> idle (explicitly assign)
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                if "idle" in group_ids:
                    final_assignments[cid] = "idle"
                else:
                    prev = self.prev_assignments.get(cid)
                    final_assignments[cid] = prev if prev in group_ids else (protecting_group(primary.id) if protecting_group(primary.id) in group_ids else (group_ids[0] if group_ids else "idle"))

        # Execute assignments and update stability counters
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