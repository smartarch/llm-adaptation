Analysis and fix

The failing tests were caused by a KeyError when accessing history inside selection_key: I built comp_hist with the key 'hist_group' but some code accessed 'group'. I fixed all such accesses to consistently use 'hist_group'. I also cleaned up other small inconsistencies (using comp_hist safely via .get where needed).

No change in the overall strategy — still prioritizes arrival time (distance/speed), prefers already-protecting and stable drones, and tries to fully protect the most threatened field and then high value-per-drone fields until at least half the fleet protects.

Updated implementation:

```py
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: comp_id -> {'group': str, 'consecutive': int}
        self._history = {}
        # parameters tuned for a balance of stability and responsiveness
        self._speed = 2.0
        self._stability_threshold = 3  # steps a drone must have stayed to be considered "stable"
        # moving a stable drone requires extra cost (multiplier) to prefer not to move it
        self._stable_move_penalty = 1.6
        # small reward multiplier for drones already protecting the target field
        self._already_protecting_bonus = 0.4

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
        # arrival time assuming straight-line at fixed speed; if already protecting this field -> 0
        if comp.state == "protecting" and comp.target_id == field.id:
            return 0.0
        dist = self._dist(comp, field)
        return dist / max(1e-6, self._speed)

    def assign_drones(self, components, environment, group_ids, step: int):
        comps = list(components)
        total_drones = len(comps)
        half_needed = (total_drones + 1) // 2  # ceil half

        # Helper to get perceived current group
        def perceived_group(comp):
            if comp.state == "idle" or comp.target_id is None:
                return "idle"
            return f"protecting {comp.target_id}"

        # Build fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats: assign all to idle
            for comp in comps:
                environment.assign_group(comp, "idle")
                cid = id(comp)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # choose primary: highest threat_level, tie by id string
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        primary = fields[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # fallback: assign idle if group not available
            for comp in comps:
                environment.assign_group(comp, "idle")
                cid = id(comp)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # Precompute history/info for comps
        comp_hist = {}
        for c in comps:
            cid = id(c)
            hist = self._history.get(cid, {'group': None, 'consecutive': 0})
            comp_hist[c] = {
                'hist_group': hist.get('group', None),
                'consecutive': hist.get('consecutive', 0),
                'current_group': perceived_group(c),
                'state': c.state,
                'target_id': c.target_id
            }

        # Determine number needed for primary
        try:
            needed_primary = int(getattr(primary, "drones_for_full_protection", 0))
        except Exception:
            needed_primary = 0
        needed_primary = max(0, needed_primary)
        needed_primary = min(needed_primary, total_drones)

        # Count current protectors for primary
        current_protectors = [c for c in comps if (c.state == "protecting" and c.target_id == primary.id)]
        # If currently fully protected exactly, keep those drones there and don't reassign them
        assigned = {}

        if len(current_protectors) >= needed_primary and needed_primary > 0:
            # Keep exactly needed_primary of current_protectors (prefer the most stable/closest)
            def keep_key(c):
                hist = comp_hist.get(c, {'consecutive': 0})
                arr = self._arrival_time(c, primary)
                # prefer larger consecutive, then closer (larger consecutive -> sort earlier by negative)
                return (-hist.get('consecutive', 0), arr)
            cur_sorted = sorted(current_protectors, key=keep_key)
            keep = set(cur_sorted[:needed_primary])
            for c in keep:
                assigned[c] = primary_group
        else:
            # select best drones by arrival time with stability penalty and bonus for already protecting
            def selection_key(c, field):
                hist = comp_hist.get(c, {'hist_group': None, 'consecutive': 0})
                arr = self._arrival_time(c, field)
                penalty = 1.0
                # if the drone is stable in another group, penalize moving it
                if hist.get('consecutive', 0) >= self._stability_threshold and hist.get('hist_group') is not None and hist.get('hist_group') != f"protecting {field.id}":
                    penalty = self._stable_move_penalty
                # if already protecting this field, give a bonus
                if c.state == "protecting" and c.target_id == field.id:
                    arr *= self._already_protecting_bonus
                return (penalty * arr, -hist.get('consecutive', 0))
            # sort all comps by key and choose top needed_primary
            sorted_candidates = sorted(comps, key=lambda c: selection_key(c, primary))
            for c in sorted_candidates[:needed_primary]:
                assigned[c] = primary_group

        # Keep count of protecting assigned so far
        num_protecting = sum(1 for g in assigned.values() if g != "idle")

        # Prepare remaining comps
        remaining = [c for c in comps if c not in assigned]

        # For additional fields use value_per_drone = threat_level / drones_for_full_protection
        other_fields = fields[1:]
        def field_value_per_drone(f):
            try:
                need = int(getattr(f, "drones_for_full_protection", 0))
            except Exception:
                need = 0
            if need <= 0:
                return 0.0
            return f.threat_level / need
        other_fields.sort(key=lambda f: (-field_value_per_drone(f), -f.threat_level, str(f.id)))

        # Try to fully protect additional fields until half_needed satisfied or no candidates
        for field in other_fields:
            if num_protecting >= half_needed:
                break
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            try:
                need = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                need = 0
            need = max(0, need)
            # compute currently assigned to that field
            currently_assigned = [c for c, g in assigned.items() if g == group_name]
            to_assign = max(0, need - len(currently_assigned))
            if to_assign == 0:
                continue
            if to_assign > len(remaining):
                # cannot fully protect this field now
                continue
            # Select best remaining drones for this field by same selection_key
            def sel_key(c):
                hist = comp_hist.get(c, {'hist_group': None, 'consecutive': 0})
                arr = self._arrival_time(c, field)
                penalty = 1.0
                if hist.get('consecutive', 0) >= self._stability_threshold and hist.get('hist_group') is not None and hist.get('hist_group') != f"protecting {field.id}":
                    penalty = self._stable_move_penalty
                if c.state == "protecting" and c.target_id == field.id:
                    arr *= self._already_protecting_bonus
                return (penalty * arr, -hist.get('consecutive', 0))
            remaining_sorted = sorted(remaining, key=sel_key)
            chosen = remaining_sorted[:to_assign]
            for c in chosen:
                assigned[c] = group_name
            remaining = [c for c in remaining if c not in chosen]
            num_protecting = sum(1 for g in assigned.values() if g != "idle")

        # If still fewer than half protecting, attempt a last pass to fill up using best-value fields
        if num_protecting < half_needed:
            idle_candidates = [c for c in comps if c not in assigned]
            for field in [primary] + other_fields:
                if num_protecting >= half_needed:
                    break
                group_name = f"protecting {field.id}"
                if group_name not in group_ids:
                    continue
                try:
                    need = int(getattr(field, "drones_for_full_protection", 0))
                except Exception:
                    need = 0
                need = max(0, need)
                currently_assigned = [c for c, g in assigned.items() if g == group_name]
                to_assign = max(0, need - len(currently_assigned))
                if to_assign == 0:
                    continue
                if to_assign > len(idle_candidates):
                    continue
                # choose closest idle candidates
                idle_candidates.sort(key=lambda c: self._arrival_time(c, field))
                chosen = idle_candidates[:to_assign]
                for c in chosen:
                    assigned[c] = group_name
                idle_candidates = [c for c in idle_candidates if c not in chosen]
                num_protecting = sum(1 for g in assigned.values() if g != "idle")

        # Any remaining unassigned -> idle
        for c in comps:
            if c not in assigned:
                assigned[c] = "idle"

        # Ensure no overprotection: trim extras from any protecting group beyond drones_for_full_protection
        counts = defaultdict(list)
        for c, g in assigned.items():
            counts[g].append(c)
        for f in fields:
            gname = f"protecting {f.id}"
            if gname not in counts:
                continue
            comps_assigned = counts[gname]
            try:
                max_needed = int(getattr(f, "drones_for_full_protection", 0))
            except Exception:
                max_needed = 0
            max_needed = max(0, max_needed)
            if len(comps_assigned) <= max_needed:
                continue
            # trim extras: prefer to keep drones already protecting and those with higher consecutive history and closer
            def keep_key(c):
                hist = comp_hist.get(c, {'consecutive': 0})
                arr = self._arrival_time(c, f)
                already = 0 if (c.state == "protecting" and c.target_id == f.id) else 1
                return (already, arr, -hist.get('consecutive', 0))
            comps_sorted = sorted(comps_assigned, key=keep_key)
            keep = set(comps_sorted[:max_needed])
            for c in comps_assigned:
                if c not in keep:
                    assigned[c] = "idle"

        # Execute assignments and update history
        for comp, group in assigned.items():
            environment.assign_group(comp, group)
            cid = id(comp)
            prev = self._history.get(cid)
            if prev and prev['group'] == group:
                prev['consecutive'] += 1
            else:
                self._history[cid] = {'group': group, 'consecutive': 1}
```