import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: comp_id -> {'group': str, 'consecutive': int}
        self._history = {}
        self._min_stable_steps = 2  # bias threshold: avoid moving drones that stayed >= this

    def _dist(self, comp, field):
        # compute Euclidean distance from component to field center
        try:
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = (comp.location.x - cx)
            dy = (comp.location.y - cy)
            return math.hypot(dx, dy)
        except Exception:
            return float("inf")

    def assign_drones(self, components, environment, group_ids, step: int):
        # Ensure all components are considered; components is an iterable of drone objects
        comps = list(components)
        total_drones = len(comps)
        half_needed = (total_drones + 1) // 2  # at least half of the drones (ceil)

        # Build valid protecting group names for threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # no threats: assign all to idle
            for comp in comps:
                environment.assign_group(comp, "idle")
                cid = id(comp)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # Choose primary (most threatened) field: highest threat_level, tie-break by id
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        primary = threatened_fields[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # fallback: if group name not available, put all idle (defensive)
            for comp in comps:
                environment.assign_group(comp, "idle")
                cid = id(comp)
                prev = self._history.get(cid)
                if prev and prev['group'] == "idle":
                    prev['consecutive'] += 1
                else:
                    self._history[cid] = {'group': "idle", 'consecutive': 1}
            return

        # Helper: current group as perceived by component state/target_id
        def current_group_of(comp):
            if comp.state == "idle" or comp.target_id is None:
                return "idle"
            # If moving_to_field or protecting, group name should be "protecting {field.id}"
            return f"protecting {comp.target_id}"

        # Precompute distances and history
        comp_info = {}
        for comp in comps:
            cid = id(comp)
            dist = self._dist(comp, primary)
            hist = self._history.get(cid, {'group': None, 'consecutive': 0})
            comp_info[comp] = {
                'dist': dist,
                'hist_group': hist['group'],
                'consecutive': hist['consecutive'],
                'current_group': current_group_of(comp),
                'state': comp.state,
                'target_id': comp.target_id
            }

        # Function to sort candidates for a specific field: prefer existing protectors and stable drones, then closer
        def sort_key_for_field(comp, field):
            info = comp_info[comp]
            # is_already_protecting_this_field: best (0) else 1
            already_protecting = 0 if (info['state'] == "protecting" and info['target_id'] == field.id) else 1
            # stability_penalty: prefer not to move drones that are stable in their current group
            stability_penalty = 0
            # if the drone has been in its current group for >= threshold, penalize moving it by lowering its priority to be chosen as candidate (so give it a small negative factor)
            if info['consecutive'] >= self._min_stable_steps and info['hist_group'] == f"protecting {field.id}":
                # it's already protecting this field and stable -> best possible
                stability_penalty = -1
            elif info['consecutive'] >= self._min_stable_steps and info['hist_group'] is not None:
                # if it's stable elsewhere, slightly penalize selecting it to move
                stability_penalty = 0.5
            else:
                stability_penalty = 0
            return (already_protecting, stability_penalty, info['dist'])

        # Determine needed drones for primary
        try:
            needed_primary = int(getattr(primary, "drones_for_full_protection", 0))
        except Exception:
            needed_primary = 0
        needed_primary = max(0, needed_primary)
        if needed_primary > total_drones:
            needed_primary = total_drones  # can't use more drones than exist

        # Select drones for primary field
        # Sort comps by key and take top needed_primary
        sorted_primary = sorted(comps, key=lambda c: sort_key_for_field(c, primary))
        assigned = {}  # comp -> group string

        primary_selected = set()
        for comp in sorted_primary[:needed_primary]:
            assigned[comp] = primary_group
            primary_selected.add(comp)

        # If there are already more drones "protecting primary" than needed, we must move extras away.
        # Find currently protecting comps that target this field
        current_protectors = [c for c in comps if (c.state == "protecting" and c.target_id == primary.id)]
        # If there are more current_protectors than needed_primary, we will keep only a subset (prefer those stable/closest)
        if len(current_protectors) > needed_primary:
            # choose which to keep: sort by closeness and stability, keep first needed_primary
            cur_sorted = sorted(current_protectors, key=lambda c: sort_key_for_field(c, primary))
            keep_set = set(cur_sorted[:needed_primary])
            # any current protector not in keep_set should be reassigned (will be handled later if not in assigned)
            # Ensure our assigned set matches keep_set (we already selected top by sort, should align; enforce)
            primary_selected = set()
            for comp in cur_sorted[:needed_primary]:
                assigned[comp] = primary_group
                primary_selected.add(comp)

        # Count assigned for protection so far
        num_protecting = len(primary_selected)

        # If fewer than half are protecting, attempt to fully protect additional fields in descending threat order
        remaining_comps = [c for c in comps if c not in assigned]
        # Filter remaining fields excluding primary and sort by threat desc
        other_fields = threatened_fields[1:]
        for field in other_fields:
            if num_protecting >= half_needed:
                break
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            try:
                needed = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                needed = 0
            needed = max(0, needed)
            if needed == 0:
                continue
            # If not enough remaining drones to fully protect this field, skip (prefer fully protecting)
            if needed > len(remaining_comps):
                continue
            # Sort remaining_comps by preference for this field
            # Ensure comp_info contains distances for this field; compute on the fly
            def sort_key(c):
                # compute similar to sort_key_for_field but recompute distance to this field
                try:
                    cx = (field.left + field.right) / 2.0
                    cy = (field.top + field.bottom) / 2.0
                    dx = (c.location.x - cx)
                    dy = (c.location.y - cy)
                    dist = math.hypot(dx, dy)
                except Exception:
                    dist = float("inf")
                is_protecting = 0 if (c.state == "protecting" and c.target_id == field.id) else 1
                hist = self._history.get(id(c), {'group': None, 'consecutive': 0})
                stability_penalty = 0
                if hist['consecutive'] >= self._min_stable_steps and hist['group'] == f"protecting {field.id}":
                    stability_penalty = -1
                elif hist['consecutive'] >= self._min_stable_steps and hist['group'] is not None:
                    stability_penalty = 0.5
                else:
                    stability_penalty = 0
                return (is_protecting, stability_penalty, dist)
            rem_sorted = sorted(remaining_comps, key=sort_key)
            chosen = rem_sorted[:needed]
            for c in chosen:
                assigned[c] = group_name
            num_protecting += len(chosen)
            # update remaining_comps
            remaining_comps = [c for c in remaining_comps if c not in chosen]

        # Any remaining drones -> idle
        for comp in comps:
            if comp not in assigned:
                assigned[comp] = "idle"

        # Enforce: do not overprotect any field: ensure count per field <= drones_for_full_protection
        # Build counts
        counts = defaultdict(list)  # group -> list of comps
        for c, g in assigned.items():
            counts[g].append(c)
        # For each protecting group, trim extras (preferring to keep stable ones)
        for field in threatened_fields:
            group_name = f"protecting {field.id}"
            if group_name not in counts:
                continue
            comps_assigned = counts[group_name]
            try:
                max_needed = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                max_needed = 0
            max_needed = max(0, max_needed)
            if max_needed >= len(comps_assigned):
                continue
            # Need to trim len(comps_assigned) - max_needed drones -> choose which to keep
            def keep_key(c):
                # prefer already protecting and stable and closer
                info = comp_info.get(c)
                if info is None:
                    # compute distance to this field
                    try:
                        cx = (field.left + field.right) / 2.0
                        cy = (field.top + field.bottom) / 2.0
                        dx = (c.location.x - cx)
                        dy = (c.location.y - cy)
                        dist = math.hypot(dx, dy)
                    except Exception:
                        dist = float("inf")
                    hist_group = self._history.get(id(c), {'group': None})['group']
                    consecutive = self._history.get(id(c), {'consecutive': 0})['consecutive']
                else:
                    dist = self._dist(c, field)
                    hist_group = info['hist_group']
                    consecutive = info['consecutive']
                already_protecting = 0 if (c.state == "protecting" and c.target_id == field.id) else 1
                stability_bonus = -consecutive  # larger consecutive -> prefer keep (smaller sort key)
                return (already_protecting, stability_bonus, dist)
            comps_assigned_sorted = sorted(comps_assigned, key=keep_key)
            keep = set(comps_assigned_sorted[:max_needed])
            # reassign extras to idle
            for c in comps_assigned:
                if c not in keep:
                    assigned[c] = "idle"

        # Final pass: ensure at least half drones are protecting if possible by re-evaluating leftover fields
        current_protecting_count = sum(1 for g in assigned.values() if g != "idle")
        if current_protecting_count < half_needed:
            # attempt to find any field that can be fully protected using remaining idle drones
            idle_comps = [c for c, g in assigned.items() if g == "idle"]
            for field in threatened_fields:
                group_name = f"protecting {field.id}"
                if group_name not in group_ids:
                    continue
                # skip if already fully protected in assigned
                already = [c for c, g in assigned.items() if g == group_name]
                try:
                    need = int(getattr(field, "drones_for_full_protection", 0))
                except Exception:
                    need = 0
                need = max(0, need - len(already))
                if need <= 0:
                    continue
                if need > len(idle_comps):
                    continue
                # choose closest idle_comps to field
                idle_comps.sort(key=lambda c: self._dist(c, field))
                chosen = idle_comps[:need]
                for c in chosen:
                    assigned[c] = group_name
                idle_comps = [c for c in idle_comps if c not in chosen]
                current_protecting_count = sum(1 for g in assigned.values() if g != "idle")
                if current_protecting_count >= half_needed:
                    break

        # Execute assignments and update history
        for comp, group in assigned.items():
            environment.assign_group(comp, group)
            cid = id(comp)
            prev = self._history.get(cid)
            if prev and prev['group'] == group:
                prev['consecutive'] += 1
            else:
                self._history[cid] = {'group': group, 'consecutive': 1}