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

        def protecting_group(field_id):
            return f"protecting {field_id}"

        fields = list(environment.fields)
        field_centers = {f.id: self._field_center(f) for f in fields}
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, set all drones to idle
        if not threatened:
            for c in components:
                group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, group)
                cid = id(c)
                if self.prev_assignments.get(cid) == group:
                    self.stay_counters[cid] += 1
                else:
                    self.stay_counters[cid] = 1
                self.prev_assignments[cid] = group
            return

        # Build metadata for drones
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

        # Primary field selection
        primary = max(threatened, key=lambda f: f.threat_level)
        primary_gid = protecting_group(primary.id)
        primary_req = int(getattr(primary, "drones_for_full_protection", 0))
        if primary_gid not in group_ids:
            primary_req = 0

        assigned_for_field = defaultdict(list)
        available_cids = set(comp_meta.keys())

        # Helper to pick k best available drones for a field with a simple priority
        def pick_k_for_field(field_id, k, avoid_frozen=True):
            # avoid_frozen not used here; kept for potential future extension
            candidates = []
            for cid in list(available_cids):
                m = comp_meta[cid]
                # priority categories:
                # 0: currently protecting this field
                # 1: moving to this field (target_id)
                # 2: idle
                # 3: other
                if m["state"] == "protecting" and m["target_id"] == field_id:
                    cat = 0
                elif m["target_id"] == field_id:
                    cat = 1
                elif m["state"] == "idle":
                    cat = 2
                else:
                    cat = 3
                # tie-break: lower travel time, then lower stay (prefer moving low-stay)
                candidates.append((cat, m["travel"].get(field_id, float('inf')), m["stay"], cid))
            candidates.sort(key=lambda x: (x[0], x[1], x[2]))
            picks = []
            for item in candidates[:k]:
                cid = item[3]
                picks.append(comp_meta[cid]["comp"])
            return picks

        # Fill primary: keep existing protectors (prefer high-stay), then fill with best available
        current_primary = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == primary.id]
        if len(current_primary) > primary_req:
            current_primary.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(primary.id, 0)))
            current_primary = current_primary[:primary_req]
        for cid in current_primary:
            assigned_for_field[primary.id].append(comp_meta[cid]["comp"])
            available_cids.discard(cid)

        to_add = max(0, primary_req - len(assigned_for_field[primary.id]))
        if to_add > 0:
            picks = pick_k_for_field(primary.id, to_add)
            for comp in picks:
                cid = id(comp)
                if cid in available_cids:
                    assigned_for_field[primary.id].append(comp)
                    available_cids.discard(cid)

        # Secondary fields: score by threat_per_drone and prefer fields requiring fewer drones when close
        other_fields = [f for f in threatened if f.id != primary.id]
        scored_fields = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            score = f.threat_level / req
            scored_fields.append((score, -req, f))
        scored_fields.sort(key=lambda x: (-x[0], x[1]))

        # Preserve already fully protected fields (do not move their protectors)
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            cur = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == f.id]
            if len(cur) >= req and req > 0:
                # keep exactly req of them (prefer high stay)
                cur.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(f.id, 0)))
                keep = cur[:req]
                for cid in keep:
                    assigned_for_field[f.id].append(comp_meta[cid]["comp"])
                    available_cids.discard(cid)

        # Greedy fill to reach at least min_protectors_target
        protected_count = sum(len(v) for v in assigned_for_field.values())
        for score, neg_req, f in scored_fields:
            if protected_count >= min_protectors_target:
                break
            req = int(getattr(f, "drones_for_full_protection", 0))
            already = len(assigned_for_field.get(f.id, []))
            need = max(0, req - already)
            if need == 0:
                continue
            # if not enough available drones, skip this field
            if len(available_cids) < need:
                continue
            picks = pick_k_for_field(f.id, need)
            if len(picks) < need:
                continue
            for comp in picks:
                cid = id(comp)
                if cid in available_cids:
                    assigned_for_field[f.id].append(comp)
                    available_cids.discard(cid)
                    protected_count += 1

        # Final trimming to ensure no field is overprotected
        final_assignments = {}
        for fid, comps in assigned_for_field.items():
            fobj = next((f for f in fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # keep currently protecting & high-stay first, then closest
                def keep_key(c):
                    cid = id(c)
                    state = getattr(c, "state", None)
                    target = getattr(c, "target_id", None)
                    is_current = 0 if (state == "protecting" and target == fid) else 1
                    stay = -self.stay_counters.get(cid, 0)
                    dist = self._dist(c.location, field_centers.get(fid, (0,0)))
                    return (is_current, stay, dist)
                comps_sorted = sorted(comps, key=keep_key)
                comps = comps_sorted[:req]
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # Remaining drones -> idle
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                if "idle" in group_ids:
                    final_assignments[cid] = "idle"
                else:
                    prev = self.prev_assignments.get(cid)
                    final_assignments[cid] = prev if prev in group_ids else (group_ids[0] if group_ids else "idle")

        # Apply assignments and update stay counters
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