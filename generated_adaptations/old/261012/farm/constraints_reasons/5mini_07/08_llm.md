Reasoning and strategy

Goal: reduce field damage by improving which fields we fully protect and which drones we send, while keeping stability and the previous functional constraints (always fully protect the top field; prefer closest drones; avoid overprotection; at most one partial field; at least half drones protecting most of the time).

Observed weaknesses to address
- Prior heuristic used average effective arrival; the time to fully protect a field is dominated by the slowest (last) drone to arrive. Using max arrival gives a better sense of readiness.
- Benefit-per-drone used previously didn't penalize long arrival times strongly enough. We should favor fields that are both highly threatened and quick to secure.
- Choosing additional fields greedily by threat/cap isn't always best when some fields are quick to secure (short readiness) with a good threat payoff.
- We must preserve stability strongly to avoid wasting time reassigning drones who are already protecting fields.

Improved approach
1. For each field with threat > 0, calculate for all drones an effective arrival time:
   - arrival_time = distance / SPEED
   - subtract small stability and same-group bonuses so drones already assigned to a field are favored.
   - also give bonus if drone is currently targeting/protecting that field.
2. For each field, simulate selecting its best cap drones (cap = drones_for_full_protection) and compute readiness_time = max(effective_arrival among those drones). If there are fewer available drones than cap, readiness_time is computed with available count (we will accept that if necessary).
3. Compute a field benefit metric:
   - benefit = field.threat_level / (1 + readiness_time)  (higher threat and quicker readiness => higher benefit)
   - benefit_per_drone = benefit / max(1, used_drones_for_this_field)
4. Select a set of fields to fully protect, maximizing total benefit per drone under the drone budget, using a greedy selection sorted by benefit_per_drone — but always include the top field regardless.
   - This approximates a knapsack-like selection where top field is mandatory.
5. Allocate drones to the chosen fields: for each chosen field pick the required number of drones with smallest effective arrival (from remaining pool). Prefer drones already protecting that field by bonuses.
6. If protecting_count < half of drones, allow a single partial fill for the next best remaining field, assigning the minimum number of extra drones needed to reach half (but not creating many partials).
7. Preserve drones in groups when it does not create additional partial fields; otherwise move them to idle.
8. Update stability bookkeeping.

This improves damage reduction by prioritizing fields that can be secured quickly relative to their threat and by better choosing which fields to commit drones to.

Code implementing the strategy

```py
from math import sqrt, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    SPEED = 2.0

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
        # Step bookkeeping for stability counters
        if self.last_step is None or step != self.last_step:
            self.last_step = step

        def protecting_name(fid):
            return f"protecting {fid}"

        # gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            idle_gid = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_gid)
                ck = self._comp_key(c)
                prev = self.last_group.get(ck)
                if prev == idle_gid:
                    self.stable_steps[ck] += 1
                else:
                    self.stable_steps[ck] = 0
                self.last_group[ck] = idle_gid
            return

        # sort fields by threat desc for deterministic ordering (top field priority)
        fields.sort(key=lambda f: (-f.threat_level, f.id))

        total_drones = len(components)
        available = set(components)
        selected = {}  # comp -> group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # precompute caps and group mapping
        field_caps = {}
        field_by_gid = {}
        for f in fields:
            gid = protecting_name(f.id)
            field_caps[gid] = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            field_by_gid[gid] = f

        # effective arrival time (lower is better) with bonuses for stability/previous assignments
        def effective_arrival(comp, field, group_name):
            dist = self._distance(comp, field)
            arrival = dist / self.SPEED
            ck = self._comp_key(comp)
            # stability bonus: favor drones that stayed in same group longer
            stab = min(self.stable_steps.get(ck, 0), 6) * 0.5
            prev = self.last_group.get(ck)
            same_group_bonus = 2.0 if prev == group_name else 0.0
            target_bonus = 1.0 if getattr(comp, "target_id", None) == field.id else 0.0
            protecting_bonus = 2.0 if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == field.id else 0.0
            eff = arrival - (stab + same_group_bonus + target_bonus + protecting_bonus)
            return max(0.0, eff)

        # For each field, compute the best set of up-to-cap drones and readiness_time = max arrival among selected
        field_candidates = []
        for f in fields:
            gid = protecting_name(f.id)
            cap = field_caps.get(gid, 0)
            if cap <= 0:
                continue
            # compute effective arrivals for all drones
            arrivals = []
            for c in components:
                arrivals.append((effective_arrival(c, f, gid), c))
            arrivals.sort(key=lambda x: x[0])
            # determine used_count: if fewer drones than cap, use all (we'll still compute benefit)
            used_count = min(cap, len(arrivals))
            if used_count == 0:
                continue
            selected_arrivals = arrivals[:used_count]
            readiness_time = max(a for a, _ in selected_arrivals)
            # benefit: favor high threat and quick readiness; divide by used_count to get per-drone metric
            benefit = getattr(f, "threat_level", 0) / (1.0 + readiness_time)
            benefit_per_drone = benefit / max(1, used_count)
            field_candidates.append({
                "field": f,
                "gid": gid,
                "cap": cap,
                "used_count": used_count,
                "readiness": readiness_time,
                "benefit": benefit,
                "benefit_per_drone": benefit_per_drone,
                "best_drones_ordered": [c for _, c in selected_arrivals]
            })

        if not field_candidates:
            # nothing valid: idle
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

        # ensure top field is included
        top_field = fields[0]
        top_gid = protecting_name(top_field.id)
        # find top candidate entry
        top_entry = next((e for e in field_candidates if e["gid"] == top_gid), None)
        # If top field has no cap (cap==0), we just continue; otherwise include it
        chosen_fields = []
        if top_entry:
            chosen_fields.append(top_entry)

        # Greedy select additional fields by benefit_per_drone, but avoid selecting fields that overlap drone choice too much
        remaining_budget = total_drones - sum(e["used_count"] for e in chosen_fields)
        # create a copy list of candidates excluding already chosen
        candidates_sorted = sorted((e for e in field_candidates if e not in chosen_fields),
                                   key=lambda x: (-x["benefit_per_drone"], -x["benefit"], x["readiness"]))
        # greedily add fields while respecting drone budget and preferring higher benefit_per_drone
        for e in candidates_sorted:
            if remaining_budget <= 0:
                break
            needed = e["cap"]
            if needed <= remaining_budget:
                chosen_fields.append(e)
                remaining_budget -= needed
            else:
                # don't partially select here; we'll maybe use one partial field later
                continue

        # Now allocate actual drones to each chosen field, picking best available drones per field
        assigned = {}  # comp -> gid
        available_drones = set(components)
        # To reduce churn, process fields ordered by benefit_per_drone descending (higher priority first)
        chosen_fields.sort(key=lambda x: (-x["benefit_per_drone"], x["readiness"]))
        for e in chosen_fields:
            f = e["field"]
            gid = e["gid"]
            cap = e["cap"]
            # pick best cap drones from available by effective arrival
            arrivals = []
            for c in available_drones:
                arrivals.append((effective_arrival(c, f, gid), c))
            arrivals.sort(key=lambda x: x[0])
            pick = [c for _, c in arrivals[:cap]]
            # if not enough available (rare), pick all
            for c in pick:
                assigned[c] = gid
                available_drones.discard(c)

        protecting_count = sum(1 for g in assigned.values() if g != idle_group)
        min_protectors_target = ceil(total_drones / 2.0)

        # If protection count < half, allow one partial fill: pick the best remaining field by benefit_per_drone
        partial_assigned_gid = None
        if protecting_count < min_protectors_target:
            # evaluate remaining fields not chosen yet
            remaining_fields = [e for e in field_candidates if e["gid"] not in [ch["gid"] for ch in chosen_fields]]
            if remaining_fields:
                # compute how many drones we need to reach half
                need = min_protectors_target - protecting_count
                # select field with highest benefit_per_drone and capacity to take drones
                remaining_fields.sort(key=lambda x: (-x["benefit_per_drone"], x["readiness"]))
                for e in remaining_fields:
                    gid = e["gid"]
                    cap = e["cap"]
                    # number already assigned to gid (likely 0)
                    already = sum(1 for g in assigned.values() if g == gid)
                    rem_cap = max(0, cap - already)
                    if rem_cap <= 0:
                        continue
                    assign_count = min(need, rem_cap, len(available_drones))
                    if assign_count <= 0:
                        continue
                    # pick assign_count best drones
                    arrivals = []
                    for c in available_drones:
                        arrivals.append((effective_arrival(c, e["field"], gid), c))
                    arrivals.sort(key=lambda x: x[0])
                    pick = [c for _, c in arrivals[:assign_count]]
                    for c in pick:
                        assigned[c] = gid
                        available_drones.discard(c)
                    protecting_count += assign_count
                    partial_assigned_gid = gid
                    break

        # Remaining drones: try to preserve previous protecting assignments only if they do not create new partials.
        assigned_counts = defaultdict(int)
        for c, g in assigned.items():
            assigned_counts[g] += 1

        for c in list(available_drones):
            ck = self._comp_key(c)
            prev = self.last_group.get(ck)
            assigned_flag = False
            if prev and prev.startswith("protecting ") and prev in field_caps:
                cap = field_caps[prev]
                already = assigned_counts.get(prev, 0)
                # If prev group is fully protected by our chosen full selections, we shouldn't add more (overprotect),
                # but if it's the chosen partial group and has remaining cap, we may keep this drone there.
                if already >= cap:
                    assigned_flag = False
                else:
                    if prev == partial_assigned_gid:
                        assigned[c] = prev
                        assigned_counts[prev] += 1
                        assigned_flag = True
            if not assigned_flag:
                assigned[c] = idle_group
            if c in available_drones:
                available_drones.discard(c)

        # Final safety trim: ensure no group exceeds cap
        group_to_comps = defaultdict(list)
        for comp, gid in assigned.items():
            group_to_comps[gid].append(comp)

        for gid, comps in list(group_to_comps.items()):
            if gid.startswith("protecting ") and gid in field_caps:
                cap = field_caps[gid]
                if len(comps) > cap:
                    f = field_by_gid.get(gid)
                    comps_sorted = sorted(comps, key=lambda c: (effective_arrival(c, f, gid), 0 if self.last_group.get(self._comp_key(c)) == gid else 1))
                    keep = comps_sorted[:cap]
                    remove = comps_sorted[cap:]
                    for c in remove:
                        assigned[c] = idle_group
                    group_to_comps[gid] = keep

        # Commit assignments and update stability tracking
        for comp in components:
            gid = assigned.get(comp, idle_group)
            environment.assign_group(comp, gid)
            ck = self._comp_key(comp)
            prev = self.last_group.get(ck)
            if prev == gid:
                self.stable_steps[ck] += 1
            else:
                self.stable_steps[ck] = 0
            self.last_group[ck] = gid
```