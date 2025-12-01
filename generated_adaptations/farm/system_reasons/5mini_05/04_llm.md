Reasoning and strategy

Goal: reduce damage by making smarter, more anticipatory drone assignments while preserving stability and the functional requirements. Improvements over the previous strategy:

- Account for travel time: drones move at speed 2, so distance / 2 gives estimated arrival time. Fields that can be reached quickly by the required number of drones are preferable because protection becomes effective sooner.
- Use a value-per-drone metric for additional fields: score = threat_level / (drones_needed * (1 + avg_arrival_time_of_k_closest_drones)). This favors high-threat fields that require fewer drones and can be reached fast.
- Greedy selection of fields to fully protect (after always fully protecting the top-threat field). This helps fully protect fewer high-impact fields rather than partially protecting many.
- Stability: prefer to keep drones that are already protecting their fields (higher stay_counters) to avoid churn; when we must move drones, prefer those with lower stay counters (less cost in stability).
- Avoid overprotection: if a field has more drones than required, trim extras (prefer to keep the highest-stability ones).
- Always ensure at least half the fleet is used for protection if possible (min_protectors_target).
- When choosing drones for a field, pick those that minimize arrival time and have low stability cost.

The code implements these heuristics and updates internal bookkeeping (prev_assignments and stay_counters) to maintain stability across steps.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_assignments = {}
        self.stay_counters = defaultdict(int)
        self.last_step_seen = {}

        # Drone speed given in problem statement
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
        min_protectors_target = math.ceil(total_drones / 2)  # aim at least half protecting

        # Prepare centers for fields
        fields = list(environment.fields)
        field_centers = {f.id: self._field_center(f) for f in fields}
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to get protecting group name
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # If no threats, set all to idle explicitly
        if not threatened_fields:
            for c in components:
                target_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, target_group)
                cid = id(c)
                prev = self.prev_assignments.get(cid)
                if prev == target_group:
                    self.stay_counters[cid] = self.stay_counters.get(cid, 0) + 1
                else:
                    self.stay_counters[cid] = 1
                self.prev_assignments[cid] = target_group
                self.last_step_seen[cid] = step
            return

        # Build metadata for every component: distances and travel times to each field
        comp_meta = {}
        for c in components:
            cid = id(c)
            prev_group = self.prev_assignments.get(cid)
            stay = self.stay_counters.get(cid, 0)
            state = getattr(c, "state", None)
            target_id = getattr(c, "target_id", None)
            loc = c.location
            dist_map = {}
            travel_map = {}
            for f in fields:
                center = field_centers[f.id]
                d = self._dist(loc, center)
                dist_map[f.id] = d
                travel_map[f.id] = d / self.drone_speed
            comp_meta[cid] = {
                "comp": c,
                "state": state,
                "target_id": target_id,
                "prev_group": prev_group,
                "stay": stay,
                "dist": dist_map,
                "travel": travel_map
            }

        # Determine primary field (highest threat)
        primary_field = max(threatened_fields, key=lambda f: f.threat_level)
        primary_gid = protecting_group(primary_field.id)

        # Containers for assignments
        assigned_for_field = defaultdict(list)  # field_id -> list of components
        available_cids = set(comp_meta.keys())

        # Helper to pick k best available drones for a given field id, preferring:
        # 1) drones already protecting that field (state == 'protecting' and target matches),
        # 2) drones already moving to that field,
        # 3) idle drones,
        # 4) others.
        # Within tie, prefer lower travel time then lower stay (move low-stay first).
        def pick_k_for_field(field_id, k, exclude_cids=None):
            if exclude_cids is None:
                exclude_cids = set()
            candidates = []
            for cid, m in comp_meta.items():
                if cid not in available_cids:
                    continue
                if cid in exclude_cids:
                    continue
                comp = m["comp"]
                score_state = 4
                if m["state"] == "protecting" and m["target_id"] == field_id:
                    score_state = 0
                elif m["prev_group"] == protecting_group(field_id):
                    score_state = 1
                elif m["target_id"] == field_id:
                    score_state = 2
                elif m["state"] == "idle":
                    score_state = 3
                # sort key: prefer small state, small travel time, small stay
                candidates.append( (score_state, m["travel"].get(field_id, float('inf')), m["stay"], cid) )
            candidates.sort(key=lambda x: (x[0], x[1], x[2]))
            picks = [comp_meta[cid]["comp"] for _,_,_,cid in candidates[:k]]
            return picks

        # 1) Handle primary field: always fully protect it using closest drones, but keep existing protectors where reasonable
        primary_required = int(getattr(primary_field, "drones_for_full_protection", 0))
        if primary_gid not in group_ids:
            # if group doesn't exist, fallback to not assigning to it (should not happen by spec)
            primary_required = 0

        # Find current protectors for primary
        current_protectors = []
        for cid, m in comp_meta.items():
            if m["state"] == "protecting" and m["target_id"] == primary_field.id:
                current_protectors.append(cid)
        # If more than required, trim extras (keep those with higher stay to maintain stability)
        if len(current_protectors) > primary_required:
            # sort by stay desc (prefer to keep high stay), then distance asc
            current_protectors.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(primary_field.id, 0)))
            keep = current_protectors[:primary_required]
            remove = current_protectors[primary_required:]
            for cid in remove:
                # make them available
                # (they already are in available_cids if not reserved; ensure they are)
                # But they were counted as protecting, so ensure they are available to reassign
                # We'll leave availability handling consistent: we'll not block them
                pass
            current_protectors = keep
        # Reserve current_protectors
        for cid in current_protectors:
            assigned_for_field[primary_field.id].append(comp_meta[cid]["comp"])
            if cid in available_cids:
                available_cids.remove(cid)

        # Need to pick additional drones if current_protectors < required
        need = max(0, primary_required - len(current_protectors))
        if need > 0:
            picks = pick_k_for_field(primary_field.id, need)
            # Add picks and remove from available_cids
            for comp in picks:
                cid = id(comp)
                if cid in available_cids:
                    assigned_for_field[primary_field.id].append(comp)
                    available_cids.remove(cid)

        # 2) Now consider other fields: compute a score for each (value per drone accounting travel time)
        other_fields = [f for f in threatened_fields if f.id != primary_field.id]
        field_scores = []
        # Pre-calc how many already protecting (and reserve them) for non-primary fields if they exist but do not auto-keep more than required
        current_protectors_map = {}
        for f in other_fields:
            cur = []
            for cid, m in comp_meta.items():
                if m["state"] == "protecting" and m["target_id"] == f.id:
                    cur.append(cid)
            # If cur > required, trim extras: keep highest stay ones
            req = int(getattr(f, "drones_for_full_protection", 0))
            if len(cur) > req:
                cur.sort(key=lambda cid: (-comp_meta[cid]["stay"], comp_meta[cid]["dist"].get(f.id, 0)))
                cur = cur[:req]
            current_protectors_map[f.id] = cur
            # Reserve them tentatively (we may decide not to protect this field)
            # For now, do not remove them from available_cids; we'll account when we decide to protect the field.

        # For scoring, for each field compute the avg travel time of k closest available drones
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            # Count already protecting (we prefer to keep them if we decide to protect this field)
            already_protecting = len([cid for cid in current_protectors_map.get(f.id, []) if cid in available_cids or True])
            need_new = max(0, req - already_protecting)
            # Gather travel times of available drones (including those not currently protecting any chosen field)
            travel_times = []
            for cid in list(available_cids):
                travel_times.append(comp_meta[cid]["travel"].get(f.id, float('inf')))
            # If we have some current_protectors not in available (they're in available too but maybe), account for them
            # Sort travel times
            travel_times.sort()
            if len(travel_times) < need_new:
                # Not enough available drones to fully protect if we don't move other protectors; penalize heavily:
                avg_time = sum(travel_times[:len(travel_times)]) / max(1, len(travel_times)) if travel_times else float('inf')
                # Set score low
                score = 0.0
            else:
                if need_new == 0:
                    # No new drones required; very good score (almost instant)
                    avg_time = 0.0
                else:
                    avg_time = sum(travel_times[:need_new]) / need_new
                # Score: threat per drone adjusted by arrival time (1 + avg_time)
                score = (f.threat_level) / (req * (1.0 + avg_time))
            field_scores.append( (score, f, need_new, req, avg_time) )

        # Sort fields by descending score
        field_scores.sort(key=lambda x: (-x[0], -x[1].threat_level))

        # Decide which fields to fully protect greedily until we reach target protection count or run out of drones
        protected_count = len(assigned_for_field[primary_field.id])
        chosen_fields = []
        # For non-primary fields that already have some current_protectors: if we choose to protect them, keep those protectors
        for score, f, need_new, req, avg_time in field_scores:
            if score <= 0:
                continue
            # Check available drones count
            if need_new > len(available_cids):
                # not enough free drones to fulfill this field without moving already-protecting drones that we reserved elsewhere
                # we skip if fulfilling requirement would force moving too many stable protectors; but we might still consider if it helps reach min_protectors_target
                # For simplicity, allow if by moving lower-stay protectors we can do it: compute total usable = available + count of current_protectors for other fields that are above their req
                # We will avoid complicated reassign; so skip if not enough available
                continue
            # Greedy stop condition: if we already reached min_protectors_target, break (we prefer fewer fields fully protected)
            if protected_count >= min_protectors_target:
                break
            # Accept this field
            chosen_fields.append((f, need_new, req))
            protected_count += (req if need_new > 0 else 0)  # approximate increase (if some already protecting counted later)
            # Reserve no actual removal now; we'll assign concretely below, removing available cids as we pick drones

        # 3) For chosen fields, assign drones: keep current protectors, then pick needed from available pool
        for f, need_new, req in chosen_fields:
            fid = f.id
            # Keep current protectors that exist (and remove them from available if present)
            current = current_protectors_map.get(fid, [])
            kept = []
            for cid in current:
                # Only keep up to req
                if len(kept) >= req:
                    break
                kept.append(cid)
            # Add kept to assignment
            for cid in kept:
                if cid in available_cids:
                    available_cids.remove(cid)
                assigned_for_field[fid].append(comp_meta[cid]["comp"])
            # Determine how many we still need
            still_need = max(0, req - len(assigned_for_field[fid]))
            if still_need <= 0:
                continue
            # Pick from available pool
            picks = pick_k_for_field(fid, still_need)
            for comp in picks:
                cid = id(comp)
                if cid in available_cids:
                    assigned_for_field[fid].append(comp)
                    available_cids.remove(cid)

        # 4) After greedy allocation, ensure we used at least min_protectors_target if possible:
        # If not yet met, consider additional best remaining fields by score and fill them if possible
        protected_now = sum(len(lst) for lst in assigned_for_field.values())
        if protected_now < min_protectors_target:
            # Consider remaining fields sorted by threat/drones ratio (simple)
            remaining_fields = sorted(
                [f for f in threatened_fields if f.id not in assigned_for_field],
                key=lambda f: (-f.threat_level / max(1, getattr(f, "drones_for_full_protection", 1)), -f.threat_level)
            )
            for f in remaining_fields:
                if protected_now >= min_protectors_target:
                    break
                req = int(getattr(f, "drones_for_full_protection", 0))
                if req <= 0:
                    continue
                if req > len(available_cids):
                    continue
                # pick k
                picks = pick_k_for_field(f.id, req)
                if len(picks) < req:
                    continue
                for comp in picks:
                    cid = id(comp)
                    if cid in available_cids:
                        assigned_for_field[f.id].append(comp)
                        available_cids.remove(cid)
                protected_now = sum(len(lst) for lst in assigned_for_field.values())

        # 5) Build final assignments dictionary, enforcing not to overprotect fields (trim based on distance/stay)
        final_assignments = {}
        for fid, comps in assigned_for_field.items():
            # Retrieve field object to get required number
            fobj = next((f for f in fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # Sort comps by (currently_protecting and target match -> prefer), then by travel time to that field, then by stay desc
                comps_sorted = sorted(
                    comps,
                    key=lambda c: (
                        0 if (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid) else 1,
                        self._dist(c.location, field_centers.get(fid, self._field_center(fobj) if fobj else (0,0))),
                        -self.stay_counters.get(id(c), 0)
                    )
                )
                comps = comps_sorted[:req]
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # 6) Remaining drones -> idle or kept in previous group if no idle
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                if "idle" in group_ids:
                    final_assignments[cid] = "idle"
                else:
                    # fallback: keep previous group if valid, else pick first valid group_id
                    prev = self.prev_assignments.get(cid)
                    if prev in group_ids:
                        final_assignments[cid] = prev
                    elif primary_gid in group_ids and primary_field.id in assigned_for_field and len(assigned_for_field[primary_field.id]) < primary_required:
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
            self.last_step_seen[cid] = step