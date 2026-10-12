from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    SmartFarmAdaptation implements the strategy described:
    - Always fully protect the most threatened field with the closest drones
    - Avoid overprotection
    - Try to fully protect other fields if resources allow
    - Keep at least half the drones in protection most of the time
    - Discourage frequent drone reassignment by tracking recent changes
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history keyed by id(component) -> (group_id, start_step)
        self._history = {}
        # minimal number of steps a drone should stay before being moved (soft constraint)
        self.MIN_STAY_STEPS = 3
        # penalty added to distance for drones that moved recently (to avoid churn)
        self.PENALTY_DISTANCE = 50.0

    def _infer_group(self, component):
        """
        Infer the current group of a drone from its observable attributes.
        """
        if getattr(component, "state", None) == "idle" or getattr(component, "target_id", None) is None:
            return "idle"
        # if the drone is moving_to_field or protecting, and has a target, that group's name:
        return f"protecting {component.target_id}"

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone_loc, point):
        dx = drone_loc.x - point[0]
        dy = drone_loc.y - point[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of targetable fields (threat_level > 0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # Map components by inferred current group and update history
        current_group_map = {}  # group_id -> list of components
        comp_key = lambda c: id(c)

        for comp in components:
            group = self._infer_group(comp)
            current_group_map.setdefault(group, []).append(comp)
            key = comp_key(comp)
            hist = self._history.get(key)
            if hist is None:
                # first time seeing this drone
                self._history[key] = (group, step)
            else:
                prev_group, start_step = hist
                if prev_group != group:
                    # group changed, reset start_step
                    self._history[key] = (group, step)
                # otherwise keep existing start_step

        # If there are no threatened fields, send everyone to idle
        if not fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                    self._history[comp_key(comp)] = ("idle", step)
            return

        # Helper: check group name validity before assignment
        def valid_group(name):
            return name in group_ids

        # Find most threatened field
        fields_sorted = sorted(fields, key=lambda f: (-f.threat_level, f.id))
        most_threatened = fields_sorted[0]

        # Precompute: centers and distances of drones to each field center
        field_centers = {f.id: self._field_center(f) for f in fields_sorted}
        drone_info = []
        for comp in components:
            key = comp_key(comp)
            loc = comp.location
            # compute distance to most threatened field (we'll compute others if needed)
            d = self._distance(loc, field_centers[most_threatened.id])
            # record base info
            current_group = self._infer_group(comp)
            hist_group, hist_start = self._history.get(key, (current_group, step))
            time_in_group = step - hist_start
            drone_info.append({
                "comp": comp,
                "key": key,
                "loc": loc,
                "current_group": current_group,
                "time_in_group": time_in_group,
                "dist_to_most": d
            })

        # We'll build desired assignments here
        desired = {}  # comp_key -> group_name

        # Helper to select N best drones for a given field id from available list
        def select_best_drones_for_field(field, available):
            center = field_centers[field.id]
            scored = []
            for info in available:
                comp = info["comp"]
                key = info["key"]
                base_dist = self._distance(comp.location, center)
                # If drone recently moved (time_in_group < MIN_STAY_STEPS) and it's currently in a different group,
                # add a modest penalty to discourage reassigning.
                penalty = 0.0
                if info["current_group"] != f"protecting {field.id}" and info["time_in_group"] < self.MIN_STAY_STEPS:
                    penalty = self.PENALTY_DISTANCE
                scored.append((base_dist + penalty, base_dist, info))
            # sort by effective distance (with penalty), tie-break by raw distance (closer prefer),
            # and favor drones already assigned to the target field by pushing them earlier
            scored.sort(key=lambda t: (t[0], t[1], 0 if t[2]["current_group"] == f"protecting {field.id}" else 1))
            return [item[2] for item in scored]  # return info dicts ordered

        # --- 1) Ensure full protection for the most threatened field ---
        top_field = most_threatened
        top_needed = max(0, getattr(top_field, "drones_for_full_protection", 0))

        # Determine currently assigned drones to top field (count only drones whose current_group matches)
        current_top_group = f"protecting {top_field.id}"
        currently_assigned_to_top = current_group_map.get(current_top_group, []).copy()

        # If more than needed currently present, release extra (prefer to release those with shortest time_in_group)
        if len(currently_assigned_to_top) > top_needed:
            # sort by time in group ascending (release newest), but also prefer to release far ones
            def release_sort_key(comp):
                key = comp_key(comp)
                hist_group, start = self._history.get(key, (self._infer_group(comp), step))
                time = step - start
                dist = self._distance(comp.location, field_centers[top_field.id])
                return (time, -dist)  # release shortest time first; among those, release farthest (so -dist)
            currently_assigned_to_top.sort(key=release_sort_key)
            # keep only the first top_needed to remain
            keep = set(currently_assigned_to_top[:top_needed])
            # mark kept drones as desired protecting group
            for comp in keep:
                desired[comp_key(comp)] = current_top_group
        else:
            # keep all currently assigned ones
            for comp in currently_assigned_to_top:
                desired[comp_key(comp)] = current_top_group

        # Determine how many more we need (if any)
        already_assigned_count = sum(1 for v in desired.values() if v == current_top_group)
        remaining_needed = top_needed - already_assigned_count

        # Build available drone list excluding ones already chosen
        chosen_keys = set(desired.keys())
        available_infos = [info for info in drone_info if info["key"] not in chosen_keys]

        if remaining_needed > 0:
            # pick the best remaining_needed drones (closest, with soft penalty for recent movers)
            ordered = select_best_drones_for_field(top_field, available_infos)
            pick = ordered[:remaining_needed]
            for info in pick:
                desired[info["key"]] = current_top_group
            # remove picked from available_infos
            picked_keys = set(info["key"] for info in pick)
            available_infos = [info for info in available_infos if info["key"] not in picked_keys]

        # --- 2) Try to fully protect other high-threat fields if resources remain ---
        # We'll iterate other fields in descending threat order
        assigned_protection_count = sum(1 for g in desired.values() if g.startswith("protecting "))
        total_drones = len(components)
        remaining_available = [info for info in drone_info if info["key"] not in desired]

        for field in fields_sorted[1:]:
            if not remaining_available:
                break
            needed = max(0, getattr(field, "drones_for_full_protection", 0))
            if needed <= 0:
                continue
            # If not enough remaining drones to fully protect this field, skip for now (we want full protection preference)
            if len(remaining_available) < needed:
                continue
            # select best drones
            ordered = select_best_drones_for_field(field, remaining_available)
            pick = ordered[:needed]
            for info in pick:
                desired[info["key"]] = f"protecting {field.id}"
            # remove from remaining_available
            picked_keys = set(info["key"] for info in pick)
            remaining_available = [info for info in remaining_available if info["key"] not in picked_keys]
            assigned_protection_count += len(pick)

        # --- 3) Ensure at least half drones are used for protection ---
        min_protection = (total_drones + 1) // 2  # at least half (rounded up) most of the time
        if sum(1 for v in desired.values() if v.startswith("protecting ")) < min_protection:
            # try to assign more drones to the next best fields (even partially)
            remaining_available = [info for info in drone_info if info["key"] not in desired]
            # consider fields sorted by threat descending (including the top one if it could accept more? but we don't overprotect)
            for field in fields_sorted:
                if not remaining_available:
                    break
                group_name = f"protecting {field.id}"
                # allowed capacity = min_protection - current_protection_count or field's remaining capacity if full protection possible
                current_assigned_to_field = sum(1 for k, g in desired.items() if g == group_name)
                # maximum allowed for this field is drones_for_full_protection minus currently assigned
                max_for_field = max(0, getattr(field, "drones_for_full_protection", 0) - current_assigned_to_field)
                # But we also can assign partials to reach min_protection, so we allow at least some even if it won't fill fully.
                need_to_reach_min = min_protection - sum(1 for v in desired.values() if v.startswith("protecting "))
                if need_to_reach_min <= 0:
                    break
                # number we may assign here:
                assign_here = min(len(remaining_available), need_to_reach_min, max_for_field if max_for_field > 0 else need_to_reach_min)
                if assign_here <= 0:
                    # If field has zero remaining capacity toward full protection, but we still need to reach min_protection,
                    # allow partial assignment (this makes sense to reduce idle drones). We'll allow assignment of up to need_to_reach_min.
                    if max_for_field == 0:
                        assign_here = min(len(remaining_available), need_to_reach_min)
                    else:
                        continue
                # pick best available drones for this field
                ordered = select_best_drones_for_field(field, remaining_available)
                pick = ordered[:assign_here]
                for info in pick:
                    desired[info["key"]] = group_name
                picked_keys = set(info["key"] for info in pick)
                remaining_available = [info for info in remaining_available if info["key"] not in picked_keys]

        # --- 4) Any drone not assigned yet -> idle ---
        for info in drone_info:
            key = info["key"]
            if key not in desired:
                desired[key] = "idle"

        # --- 5) Perform assignments via environment.assign_group and update history ---
        # Map back keys to components for assignment
        key_to_comp = {id(c): c for c in components}
        for key, group in desired.items():
            comp = key_to_comp.get(key)
            if comp is None:
                continue
            # Safety: only assign valid group ids (provided in group_ids). If group invalid, fallback to "idle"
            if not valid_group(group):
                group = "idle" if "idle" in group_ids else group_ids[0]
            environment.assign_group(comp, group)
            # update history: if changed, reset start_step; if same, keep start_step
            prev = self._history.get(key)
            if prev is None:
                self._history[key] = (group, step)
            else:
                prev_group, prev_start = prev
                if prev_group != group:
                    self._history[key] = (group, step)
                else:
                    # keep previous start
                    self._history[key] = (prev_group, prev_start)