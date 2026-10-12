Reasoning and adaptation strategy

Goal recap and thinking
- Must always fully protect the single most threatened field using the closest drones — this is non-negotiable.
- Beyond that, to reduce damage we want to maximize the protection benefit per drone: some fields require many drones to protect but have only slightly higher threat. Allocating many drones to such fields can be less efficient than fully protecting several smaller-but-still-threatened fields.
- Therefore, after securing the top field, we should prioritize filling other full-protection requirements by a heuristic that scores fields by expected benefit per drone: score = threat_level / drones_for_full_protection. This prioritizes fields that give the most threat reduction per drone invested.
- Keep stability: prefer drones already protecting a field or moving to it when selecting drones for that field, to avoid unnecessary churn. When choosing from the rest, prefer idle or moving drones over stealing active protectors from other fields.
- Ensure at least half the fleet is assigned to protect (if possible). If after the greedy full-protection allocations we still have fewer than half protecting, try to either complete the next-best fields or, if that's impossible, assign remaining drones to the highest-threat fields (closest-first) to increase the number protecting. We still avoid overprotection.
- Always avoid overprotection and call assign_group exactly once per drone.

This revised strategy concentrates drones where each drone yields the largest marginal reduction of expected damage, while still honoring the hard requirement for the most threatened field and preserving stability.

Implementation notes
- Field scoring: score = threat_level / max(1, drones_for_full_protection). This is used after the top field is secured.
- Selection order for drones for a particular field: (1) current protectors of that field, (2) drones moving to that field, (3) idle drones or drones without target, (4) other drones (prefer those closest).
- When filling the top field, we still pick the closest drones overall (distance primary) with stability as secondary key — this guarantees the "closest drones" requirement.
- Deterministic tie-breaking by field id and by sorting keys ensures stable behavior across runs.

Code follows.

```py
from typing import List, Dict
from math import hypot

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist(self, loc, cx, cy):
        try:
            return hypot(loc.x - cx, loc.y - cy)
        except Exception:
            return float("inf")

    def assign_drones(self, components, environment, group_ids, step: int):
        # No drones -> nothing to do
        if not components:
            return

        # Identify threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no fields threatened, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Deterministic ordering: primary by threat desc, tie-break by id
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Precompute centers and capacities
        field_centers = {f.id: self._field_center(f) for f in threatened_fields}
        field_capacity = {f.id: max(0, int(getattr(f, "drones_for_full_protection", 0))) for f in threatened_fields}

        # Group name helper
        def grp(fid):
            return f"protecting {fid}"

        total_drones = len(components)
        min_protect = (total_drones + 1) // 2  # ceil half

        # Containers for planned assignments
        planned: Dict[str, List] = {f.id: [] for f in threatened_fields}
        assigned_set = set()  # drones already assigned in planned

        # Helper for stability preference (lower better)
        def stability_pref(c, fid):
            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)
            if state == "protecting" and target == fid:
                return 0
            if state == "moving_to_field" and target == fid:
                return 1
            if state == "idle" or target is None:
                return 2
            if state == "protecting":
                return 3
            return 4

        # 1) Fully protect the most threatened field using the closest drones (distance primary)
        main_field = threatened_fields[0]
        main_id = main_field.id
        main_cap = field_capacity.get(main_id, 0)
        main_cx, main_cy = field_centers[main_id]

        # Sort all drones by (distance to main, stability_pref)
        all_sorted_for_main = sorted(
            components,
            key=lambda c: (self._dist(c.location, main_cx, main_cy), stability_pref(c, main_id), str(getattr(c, "target_id", "")))
        )
        # Assign top main_cap drones (or as many as available)
        for c in all_sorted_for_main[:main_cap]:
            planned[main_id].append(c)
            assigned_set.add(c)

        # 2) Score remaining fields by benefit per drone and try to fully protect as many as possible
        # Score uses threat_level / drones_required (higher is better). Skip main field.
        def field_score(f):
            req = max(1, int(getattr(f, "drones_for_full_protection", 0)))
            return (f.threat_level / req, f.threat_level, -req, str(f.id))  # tie-breakers

        other_fields = threatened_fields[1:]
        other_fields.sort(key=field_score, reverse=True)  # highest per-drone benefit first

        # Helper: get candidate list for a field, ordered by preference
        def candidates_for_field(fid):
            cx, cy = field_centers[fid]
            # Build categories
            protectors = []
            movers = []
            idles = []
            others = []
            for c in components:
                if c in assigned_set:
                    continue
                state = getattr(c, "state", None)
                target = getattr(c, "target_id", None)
                if state == "protecting" and target == fid:
                    protectors.append(c)
                elif state == "moving_to_field" and target == fid:
                    movers.append(c)
                elif state == "idle" or target is None:
                    idles.append(c)
                else:
                    others.append(c)
            # Sort each category by distance to the field center
            protectors.sort(key=lambda c: self._dist(c.location, cx, cy))
            movers.sort(key=lambda c: self._dist(c.location, cx, cy))
            idles.sort(key=lambda c: self._dist(c.location, cx, cy))
            others.sort(key=lambda c: self._dist(c.location, cx, cy))
            return protectors + movers + idles + others

        # Fill other fields greedily by score using remaining drones
        for f in other_fields:
            fid = f.id
            cap = field_capacity.get(fid, 0)
            if cap <= 0:
                continue
            needed = cap - len(planned[fid])
            if needed <= 0:
                continue
            cand = candidates_for_field(fid)
            take = cand[:needed]
            for c in take:
                planned[fid].append(c)
                assigned_set.add(c)

        # 3) If we still haven't reached minimum protecting drones, try to allocate more
        assigned_protecting_count = sum(len(lst) for lst in planned.values())
        if assigned_protecting_count < min_protect:
            # Try to complete additional fields in order of score (we reused other_fields sorted by score)
            for f in other_fields:
                if assigned_protecting_count >= min_protect:
                    break
                fid = f.id
                cap = field_capacity.get(fid, 0)
                remaining_cap = max(0, cap - len(planned[fid]))
                if remaining_cap <= 0:
                    continue
                cand = candidates_for_field(fid)
                if not cand:
                    continue
                need = min(remaining_cap, min_protect - assigned_protecting_count)
                take = cand[:need]
                for c in take:
                    planned[fid].append(c)
                    assigned_set.add(c)
                assigned_protecting_count = sum(len(lst) for lst in planned.values())

        # 4) If still not reaching min_protect and no full completions possible, assign remaining drones
        # to highest-threat fields (closest-first) until min_protect is achieved or no drones left.
        assigned_protecting_count = sum(len(lst) for lst in planned.values())
        if assigned_protecting_count < min_protect:
            # Build list of fields in threat descending order
            by_threat = sorted(threatened_fields, key=lambda f: (-f.threat_level, str(f.id)))
            remaining_drones = [c for c in components if c not in assigned_set]
            if remaining_drones:
                # Try to assign to fields without exceeding their capacity
                for f in by_threat:
                    if assigned_protecting_count >= min_protect:
                        break
                    fid = f.id
                    cap = field_capacity.get(fid, 0)
                    remaining_cap = max(0, cap - len(planned[fid]))
                    if remaining_cap <= 0:
                        continue
                    cx, cy = field_centers[fid]
                    remaining_drones.sort(key=lambda c: (self._dist(c.location, cx, cy), stability_pref(c, fid)))
                    need = min(remaining_cap, min_protect - assigned_protecting_count)
                    take = remaining_drones[:need]
                    for c in take:
                        planned[fid].append(c)
                        assigned_set.add(c)
                    # refresh lists
                    remaining_drones = [c for c in remaining_drones if c not in assigned_set]
                    assigned_protecting_count = sum(len(lst) for lst in planned.values())

        # 5) All unassigned drones -> idle
        assignment_map = {}
        # Use valid group ids; fallback to idle if group missing
        for fid, lst in planned.items():
            gname = grp(fid)
            if gname not in group_ids:
                gname = "idle"
            for c in lst:
                assignment_map[c] = gname
        for c in components:
            if c not in assignment_map:
                assignment_map[c] = "idle"

        # Apply assignments exactly once per component
        for c, g in assignment_map.items():
            environment.assign_group(c, g)
```