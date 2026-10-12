import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: comp_id -> {'group': str, 'consecutive': int}
        self._history = {}
        # parameters
        self._speed = 2.0
        # stability: small threshold to slightly prefer not moving very-stable drones
        self._stability_threshold = 3
        # small penalty multiplier when moving a stable drone (should not be huge)
        self._stable_move_penalty = 1.3

    def _dist(self, comp, field):
        try:
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = comp.location.x - cx
            dy = comp.location.y - cy
            return math.hypot(dx, dy)
        except Exception:
            return float("inf")

    def _arrival_time(self, comp, field):
        # if already protecting this field, treat arrival as 0
        if comp.state == "protecting" and comp.target_id == field.id:
            return 0.0
        # otherwise distance / speed
        dist = self._dist(comp, field)
        return dist / max(1e-6, self._speed)

    def assign_drones(self, components, environment, group_ids, step: int):
        comps = list(components)
        total = len(comps)
        half_needed = (total + 1) // 2  # ceil half

        # perceived current group for history bookkeeping
        def perceived_group(comp):
            if comp.state == "idle" or comp.target_id is None:
                return "idle"
            return f"protecting {comp.target_id}"

        # gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # nothing to protect -> idle all
            for c in comps:
                environment.assign_group(c, "idle")
                cid = id(c)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # choose primary field (highest threat, tie by id)
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        primary = fields[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # fallback: idle all
            for c in comps:
                environment.assign_group(c, "idle")
                cid = id(c)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # build comp_info and history defaults
        comp_info = {}
        for c in comps:
            cid = id(c)
            hist = self._history.get(cid, {'group': None, 'consecutive': 0})
            comp_info[c] = {
                'hist_group': hist.get('group'),
                'consecutive': hist.get('consecutive', 0),
                'state': c.state,
                'target_id': c.target_id
            }

        # helper to compute selection priority for a comp to a field
        # lower is better
        def priority(comp, field, prefer_idle_moving=False):
            info = comp_info.get(comp, {})
            arr = self._arrival_time(comp, field)
            penalty = 1.0
            hist_group = info.get('hist_group')
            consecutive = info.get('consecutive', 0)
            # if drone is very stable in some other group, slightly penalize moving it
            if consecutive >= self._stability_threshold and hist_group is not None and hist_group != f"protecting {field.id}":
                penalty = self._stable_move_penalty
            # prefer idle/moving_to_field when prefer_idle_moving is True
            # We implement this by giving them a small bonus (lower priority value)
            if prefer_idle_moving:
                if comp.state == "idle":
                    arr *= 0.8
                elif comp.state == "moving_to_field" and comp.target_id == field.id:
                    arr *= 0.7
            # but always strongly prefer ones already protecting the target field (they are already effective)
            if comp.state == "protecting" and comp.target_id == field.id:
                arr *= 0.5
            return penalty * arr, -consecutive

        # get number needed for a field safely
        def drones_needed(field):
            try:
                n = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                n = 0
            return max(0, n)

        # Assign primary field first
        needed_primary = min(drones_needed(primary), total)
        assigned = {}
        # selection order categories to minimize disruption:
        # 1) already protecting primary
        # 2) moving_to_field with target primary
        # 3) idle
        # 4) other drones (protecting other fields)
        cats = [
            [c for c in comps if c.state == "protecting" and c.target_id == primary.id],
            [c for c in comps if c.state == "moving_to_field" and c.target_id == primary.id],
            [c for c in comps if c.state == "idle"],
            [c for c in comps if c not in sum([list(x) for x in cats], [])]  # placeholder; will be replaced
        ]
        # build cats[3] now properly as those not in previous categories
        used_in_cats = set()
        cats_tmp = []
        for cat in cats[:3]:
            for c in cat:
                used_in_cats.add(c)
            cats_tmp.append(cat)
        cats_tmp.append([c for c in comps if c not in used_in_cats])
        cats = cats_tmp

        selected = []
        for cat in cats:
            # sort category by arrival_time ascending (and stability tie-break integrated in priority)
            sorted_cat = sorted(cat, key=lambda c: priority(c, primary))
            for c in sorted_cat:
                if len(selected) >= needed_primary:
                    break
                if c not in selected:
                    selected.append(c)
            if len(selected) >= needed_primary:
                break

        # if not enough selected but needed_primary > selected, fill from any comps by arrival time
        if len(selected) < needed_primary:
            remaining_pool = [c for c in comps if c not in selected]
            remaining_sorted = sorted(remaining_pool, key=lambda c: priority(c, primary))
            for c in remaining_sorted:
                if len(selected) >= needed_primary:
                    break
                selected.append(c)

        for c in selected[:needed_primary]:
            assigned[c] = primary_group

        # Now greedily select other fields to fully protect by value per drone (threat/drones_needed)
        remaining_comps = [c for c in comps if c not in assigned]
        other_fields = fields[1:]
        # compute score: higher is better; prefer small drones_needed to allow more fields to get protected
        def field_score(f):
            need = drones_needed(f)
            if need <= 0:
                return 0.0
            return (f.threat_level / need) * (1.0 + 1.0 / (1 + need))
        other_fields.sort(key=lambda f: (-field_score(f), drones_needed(f), -f.threat_level, str(f.id)))

        for f in other_fields:
            need = drones_needed(f)
            if need <= 0:
                continue
            # if we don't have enough remaining to fully protect, skip for now
            if need > len(remaining_comps):
                continue
            # choose best remaining comps preferring idle/moving first
            # sort remaining by (prefer_idle_moving=True) priority
            remaining_comps.sort(key=lambda c: priority(c, f, prefer_idle_moving=True))
            chosen = remaining_comps[:need]
            for c in chosen:
                assigned[c] = f"protecting {f.id}"
            remaining_comps = [c for c in remaining_comps if c not in chosen]

        # Count protecting now
        num_protecting = sum(1 for g in assigned.values() if g != "idle")

        # If we have fewer than half protecting, we must assign more drones.
        # We'll assign remaining drones (possibly partially) to best remaining field(s).
        if num_protecting < half_needed:
            remaining = [c for c in comps if c not in assigned]
            # Build candidate fields list including primary and others, sorted by threat (urgency) then score
            candidates = sorted(fields, key=lambda f: (-f.threat_level, -field_score(f), drones_needed(f), str(f.id)))
            # Try to fill fields (even partially) to reach half_needed. For each candidate compute how many more needed to full protect,
            # but we're willing to assign fewer than needed to reach half_needed.
            for f in candidates:
                if num_protecting >= half_needed:
                    break
                gname = f"protecting {f.id}"
                already = [c for c, g in assigned.items() if g == gname]
                already_count = len(already)
                full_need = drones_needed(f)
                # how many we can assign: either full_need - already_count or whatever needed to reach half_needed
                need_to_full = max(0, full_need - already_count)
                to_assign = min(len(remaining), max( need_to_full, half_needed - num_protecting ))
                if to_assign <= 0:
                    continue
                # pick best remaining by priority (prefer idle/moving)
                remaining.sort(key=lambda c: priority(c, f, prefer_idle_moving=True))
                chosen = remaining[:to_assign]
                for c in chosen:
                    assigned[c] = gname
                remaining = [c for c in remaining if c not in chosen]
                num_protecting = sum(1 for g in assigned.values() if g != "idle")

        # Any leftover unassigned become idle
        for c in comps:
            if c not in assigned:
                assigned[c] = "idle"

        # Ensure no overprotection: trim any protecting group beyond its drones_for_full_protection
        counts = defaultdict(list)
        for c, g in assigned.items():
            counts[g].append(c)
        for f in fields:
            gname = f"protecting {f.id}"
            comps_assigned = counts.get(gname, [])
            maxn = drones_needed(f)
            if maxn <= 0:
                # if field expects 0, don't assign protectors (move them to idle)
                for c in comps_assigned:
                    assigned[c] = "idle"
                continue
            if len(comps_assigned) <= maxn:
                continue
            # sort to decide whom to keep: prefer those with smallest arrival_time and those already protecting
            comps_sorted = sorted(comps_assigned, key=lambda c: (self._arrival_time(c, f), 0 if (c.state == "protecting" and c.target_id == f.id) else 1, -comp_info.get(c, {}).get('consecutive', 0)))
            keep = set(comps_sorted[:maxn])
            for c in comps_assigned:
                if c not in keep:
                    assigned[c] = "idle"

        # Apply assignments and update history
        for comp, group in assigned.items():
            environment.assign_group(comp, group)
            cid = id(comp)
            prev = self._history.get(cid)
            if prev and prev['group'] == group:
                prev['consecutive'] += 1
            else:
                self._history[cid] = {'group': group, 'consecutive': 1}