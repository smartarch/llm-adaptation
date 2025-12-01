Reasoning and strategy

Goals: reduce damage by more stable, targeted protection while satisfying functional requirements:
- Always fully protect the single most threatened field using the closest drones.
- Keep at least half the fleet protecting fields most of the time.
- Avoid frequent reassignment; keep many drones "frozen" in place (not moved) if they have stayed assigned for several steps.
- Prefer to fully protect fewer high-value fields (high threat per needed drone) rather than partially protect many.
- When forced to reassign drones, prefer ones that are cheap to move: low stay-counter, far from their current protected field (so their move hurts less), and close to the destination (fast arrival).

Main changes over previous attempts
- Introduce a "freeze" stability heuristic: drones that stayed assigned >= freeze_threshold steps are not moved except to protect the primary field and only if necessary. This reduces churn and preserves stability requirement.
- Primary protection selection: first keep current primary protectors, then add idle or moving-to-primary drones that arrive fastest; only then consider reassigning other drones (preferring low stay and low cost).
- Secondary field selection: compute threat_per_drone = threat_level / drones_for_full_protection and select fields in descending order, but also prefer fields requiring fewer drones to reach the minimum half-protection goal quickly.
- When selecting drones to move for secondary fields, avoid frozen drones and prefer idle or moving-to-target drones; use travel time and reassign cost to break ties.
- Always avoid overprotection (trim assigned drones to the required number).
- Update prev_assignments and stay_counters consistently; every drone is explicitly assigned each step.

This is a conservative strategy that favors stability and prioritizes fields with highest marginal benefit per drone while ensuring the most threatened field is protected by the closest/most suitable drones.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assignments = {}
        self.stay_counters = defaultdict(int)
        self.drone_speed = 2.0
        # Freeze drones that have stayed this many steps: avoid moving them unless necessary
        self.freeze_threshold = 3

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

        fields = list(environment.fields)
        field_centers = {f.id: self._field_center(f) for f in fields}
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all to idle explicitly
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

        # Build metadata
        comp_meta = {}
        for c in components:
            cid = id(c)
            dist = {}
            travel = {}
            for f in fields:
                center = field_centers[f.id]
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

        # Primary field: highest threat
        primary = max(threatened, key=lambda f: f.threat_level)
        primary_gid = protecting_group(primary.id)
        primary_req = int(getattr(primary, "drones_for_full_protection", 0))
        if primary_gid not in group_ids:
            primary_req = 0

        assigned_for_field = defaultdict(list)
        available_cids = set(comp_meta.keys())

        # Helper to determine if a drone is frozen (high stability)
        def is_frozen(cid):
            return comp_meta[cid]["stay"] >= self.freeze_threshold

        # Select drones for primary field
        # 1) Keep current protectors for primary
        current_primary = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == primary.id]
        # If more than required, keep highest-stay to preserve stability, trim extras by distance
        if len(current_primary) > primary_req:
            current_primary.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(primary.id, 0)))
            current_primary = current_primary[:primary_req]
        for cid in current_primary:
            assigned_for_field[primary.id].append(comp_meta[cid]["comp"])
            available_cids.discard(cid)

        need = max(0, primary_req - len(assigned_for_field[primary.id]))

        # 2) Fill remaining slots with best candidates
        if need > 0:
            # Build candidate list without frozen drones if possible
            def primary_candidate_score(cid):
                m = comp_meta[cid]
                # preference ordering:
                # 0: currently moving to primary (target_id == primary.id)
                # 1: idle
                # 2: protecting other field (but low stay and far from that field is preferred)
                # frozen penalized heavily
                if m["target_id"] == primary.id:
                    base = 0
                elif m["state"] == "idle":
                    base = 1
                elif m["state"] == "protecting":
                    base = 2
                else:
                    base = 3
                frozen_penalty = 1000 if is_frozen(cid) else 0
                # reassign cost: higher stay and closer to its current target means costlier to move
                reassign_cost = m["stay"] * 50
                # if protecting another field, measure proximity to its center; if far, moving is cheaper
                if m["state"] == "protecting" and m["target_id"] is not None:
                    tid = m["target_id"]
                    if tid in field_centers:
                        dist_to_own = comp_meta[cid]["dist"].get(tid, 0)
                        # being close to own field increases cost (we don't want to move a drone that's right above its field)
                        reassign_cost += max(0, 50 - dist_to_own)
                travel = m["travel"].get(primary.id, float('inf'))
                # final tuple: prefer lower base, lower frozen_penalty, lower reassign_cost, lower travel
                return (base + (1 if frozen_penalty else 0), frozen_penalty, reassign_cost, travel, comp_meta[cid]["stay"])

            # Prefer to pick non-frozen drones first
            candidates = [cid for cid in available_cids if not is_frozen(cid)]
            if len(candidates) < need:
                # include frozen as last resort
                candidates = list(available_cids)
            candidates.sort(key=primary_candidate_score)
            picks = candidates[:need]
            for cid in picks:
                assigned_for_field[primary.id].append(comp_meta[cid]["comp"])
                available_cids.discard(cid)

        # Secondary fields selection:
        # Compute threat_per_drone = threat_level / drones_required and prioritize small drone requirements
        other_fields = [f for f in threatened if f.id != primary.id]
        field_priority = []
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            score = f.threat_level / req  # simple per-drone threat value
            # prefer smaller req when scores equal
            field_priority.append((score, -req, f))
        field_priority.sort(key=lambda x: (-x[0], x[1]))

        # Keep existing fully-protected fields (do not move drones from them)
        for f in other_fields:
            gid = protecting_group(f.id)
            # find current protectors
            cur = [cid for cid, m in comp_meta.items() if m["state"] == "protecting" and m["target_id"] == f.id]
            if len(cur) >= int(getattr(f, "drones_for_full_protection", 0)):
                # keep them assigned
                for cid in cur[:int(getattr(f, "drones_for_full_protection", 0))]:
                    if cid in available_cids:
                        available_cids.discard(cid)
                    assigned_for_field[f.id].append(comp_meta[cid]["comp"])

        # Greedily pick additional fields to reach min_protectors_target
        protected_now = sum(len(v) for v in assigned_for_field.values())
        for score, neg_req, f in field_priority:
            if protected_now >= min_protectors_target:
                break
            req = int(getattr(f, "drones_for_full_protection", 0))
            already = len(assigned_for_field.get(f.id, []))
            need_k = max(0, req - already)
            if need_k == 0:
                continue
            # Build candidate cids: prefer non-frozen ones
            candidates = [cid for cid in available_cids if not is_frozen(cid)]
            if len(candidates) < need_k:
                # consider frozen as last resort, but avoid moving many frozen drones
                candidates = list(available_cids)
            # Score candidates by travel time to f and low reassign cost
            def candidate_score_for_field(cid):
                m = comp_meta[cid]
                travel = m["travel"].get(f.id, float('inf'))
                reassign_cost = m["stay"] * 40
                if m["state"] == "protecting" and m["target_id"] is not None:
                    tid = m["target_id"]
                    if tid in field_centers:
                        dist_to_own = m["dist"].get(tid, 0)
                        reassign_cost += max(0, 40 - dist_to_own)
                frozen_penalty = 1000 if is_frozen(cid) else 0
                return (frozen_penalty, reassign_cost, travel, m["stay"])
            candidates.sort(key=candidate_score_for_field)
            picks = candidates[:need_k]
            if len(picks) < need_k:
                continue
            for cid in picks:
                assigned_for_field[f.id].append(comp_meta[cid]["comp"])
                available_cids.discard(cid)
                protected_now += 1

        # Final assignments: enforce per-field caps (do not overprotect)
        final_assignments = {}
        for fid, comps in assigned_for_field.items():
            fobj = next((f for f in fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # keep those currently protecting & frozen first, then high stay, then closest
                def keep_key(c):
                    cid = id(c)
                    state = getattr(c, "state", None)
                    target = getattr(c, "target_id", None)
                    is_current = 0 if (state == "protecting" and target == fid) else 1
                    frozen_flag = 0 if is_frozen(cid) else 1  # prefer frozen to keep stability
                    stay = -self.stay_counters.get(cid, 0)  # prefer higher stay
                    dist = self._dist(c.location, field_centers.get(fid, (0,0)))
                    return (is_current, frozen_flag, stay, dist)
                comps_sorted = sorted(comps, key=keep_key)
                comps = comps_sorted[:req]
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # Remaining drones -> idle
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                # prefer to keep previous group if it's valid and we are not forced to move
                prev = self.prev_assignments.get(cid)
                if prev in group_ids and prev.startswith("protecting") and cid not in final_assignments:
                    # keep previous protecting if it's still sensible (otherwise set idle)
                    # but ensure we don't violate overprotection: prev may point to a field not selected; we avoid that
                    # safest: if prev corresponds to a field that we assigned fully, keep it; else idle
                    assigned_fields = {fid for fid in assigned_for_field.keys()}
                    if prev.startswith("protecting "):
                        prev_fid = prev.split("protecting ", 1)[1]
                        if prev_fid in assigned_fields:
                            final_assignments[cid] = prev
                            continue
                final_assignments[cid] = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Execute assignments and update tracking
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