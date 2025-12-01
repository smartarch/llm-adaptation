from typing import Dict, Any
import math
from collections import defaultdict

# Import base class
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track previous assignments and stability per drone (persistent across steps)
        # keyed by id(component)
        self.prev_assignments: Dict[int, str] = {}
        self.stable_steps: Dict[int, int] = defaultdict(int)

    def _field_center(self, field: Any):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones to groups:
        - "idle"
        - "protecting {field.id}" for fields with threat_level > 0 (group_ids provides allowed names)
        """
        # Prepare data
        total_drones = len(components)
        half_needed = (total_drones + 1) // 2  # at least half (ceil)
        # Map from component id to component object for assignment
        comp_map = {id(c): c for c in components}

        # Build list of threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if len(threatened_fields) == 0:
            # No threats: assign all drones to idle
            for c in components:
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
                    key = id(c)
                    prev = self.prev_assignments.get(key)
                    if prev == "idle":
                        self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
                    else:
                        self.stable_steps[key] = 0
                    self.prev_assignments[key] = "idle"
            return

        # Find the most threatened field (max threat_level). Tie-breaker: larger threat_level then smaller drones_for_full_protection
        most_threatened = max(threatened_fields, key=lambda f: (f.threat_level, -getattr(f, "drones_for_full_protection", 0)))

        # Helper: group name builder and check existence in group_ids
        def group_name_for(field):
            return f"protecting {field.id}"

        # Precompute distances to fields and current info
        drone_infos = []
        for c in components:
            key = id(c)
            loc = getattr(c, "location", None)
            x = getattr(loc, "x", 0) if loc else 0
            y = getattr(loc, "y", 0) if loc else 0
            prev_group = self.prev_assignments.get(key)
            stable = self.stable_steps.get(key, 0)
            state = getattr(c, "state", None)
            target_id = getattr(c, "target_id", None)
            # distance to most threatened field center
            mcx, mcy = self._field_center(most_threatened)
            dist_to_most = self._distance(x, y, mcx, mcy)
            drone_infos.append({
                "comp": c,
                "key": key,
                "x": x, "y": y,
                "prev_group": prev_group,
                "stable": stable,
                "state": state,
                "target_id": target_id,
                "dist_to_most": dist_to_most
            })

        assignments: Dict[int, str] = {}  # key -> group string
        assigned_counts_by_field = defaultdict(int)

        # 1) Assign full protection to the most threatened field using the closest drones,
        #    preferring drones already assigned to that protecting group (to avoid churn).
        main_group = group_name_for(most_threatened)
        required_main = int(getattr(most_threatened, "drones_for_full_protection", 1))
        # Only consider if group name exists in group_ids
        if main_group in group_ids:
            # Sort drones by preference:
            #   prefer prev_group == main_group (stable assignment),
            #   then prefer drones with state protecting or moving_to_field with target == field.id,
            #   then by distance
            def main_sort_key(info):
                was_prev = 0 if info["prev_group"] == main_group else 1  # 0 is best
                is_already_targeting = 0 if (info["state"] == "protecting" or info["target_id"] == most_threatened.id) else 1
                return (was_prev, is_already_targeting, info["dist_to_most"])
            sorted_main = sorted(drone_infos, key=main_sort_key)
            # Select up to required_main drones
            selected = []
            for info in sorted_main:
                if len(selected) >= required_main:
                    break
                key = info["key"]
                if key in assignments:
                    continue
                selected.append(info)
            for info in selected:
                assignments[info["key"]] = main_group
                assigned_counts_by_field[most_threatened.id] += 1

        # 2) Attempt to fully protect other fields (descending threat) using remaining drones,
        #    avoid overprotection, prefer drones already assigned to those fields
        remaining_fields = [f for f in threatened_fields if f.id != most_threatened.id]
        remaining_fields.sort(key=lambda f: f.threat_level, reverse=True)
        # Build fast access to drone distances to each field center to choose closest for other fields
        # Precompute centers
        field_centers = {f.id: self._field_center(f) for f in remaining_fields}
        # Build a list of remaining drone infos (not yet assigned)
        def get_unassigned_infos():
            return [info for info in drone_infos if info["key"] not in assignments]

        for field in remaining_fields:
            group_name = group_name_for(field)
            if group_name not in group_ids:
                continue
            need = int(getattr(field, "drones_for_full_protection", 1))
            # Count already assigned to this field (from previous assignments we kept)
            already = 0
            # consider our current assignments (if any) for this field (should be zero at this point)
            for k, g in assignments.items():
                if g == group_name:
                    already += 1
            needed_now = need - already
            if needed_now <= 0:
                continue
            # If not enough unassigned drones to meet required full protection, skip for now
            unassigned_infos = get_unassigned_infos()
            if len(unassigned_infos) < needed_now:
                continue
            # For selection prefer those with prev_group==group_name, then distance
            cx, cy = field_centers[field.id]
            for info in unassigned_infos:
                # compute distance to this field center
                info.setdefault("distances", {})[field.id] = self._distance(info["x"], info["y"], cx, cy)
            def other_sort(info):
                was_prev = 0 if info["prev_group"] == group_name else 1
                is_already_targeting = 0 if (info["state"] == "protecting" or info["target_id"] == field.id) else 1
                return (was_prev, is_already_targeting, info["distances"][field.id])
            sorted_candidates = sorted(unassigned_infos, key=other_sort)
            # select needed_now of them
            selected = sorted_candidates[:needed_now]
            for info in selected:
                assignments[info["key"]] = group_name
                assigned_counts_by_field[field.id] += 1

        # 3) After full protections, check whether at least half the drones are used for protection.
        currently_protecting = len(assignments)
        if currently_protecting < half_needed:
            # Try to fully protect additional fields if possible
            unassigned_infos = [info for info in drone_infos if info["key"] not in assignments]
            # Attempt to fully protect remaining fields in order
            for field in remaining_fields:
                if currently_protecting >= half_needed:
                    break
                group_name = group_name_for(field)
                if group_name not in group_ids:
                    continue
                need = int(getattr(field, "drones_for_full_protection", 1))
                already = assigned_counts_by_field[field.id]
                needed_now = need - already
                if needed_now <= 0:
                    continue
                unassigned_infos = [info for info in drone_infos if info["key"] not in assignments]
                if len(unassigned_infos) >= needed_now:
                    # assign closest needed_now drones
                    cx, cy = self._field_center(field)
                    for info in unassigned_infos:
                        info.setdefault("distances", {})[field.id] = self._distance(info["x"], info["y"], cx, cy)
                    sorted_candidates = sorted(unassigned_infos, key=lambda info: (0 if info["prev_group"] == group_name else 1, info["distances"][field.id]))
                    chosen = sorted_candidates[:needed_now]
                    for info in chosen:
                        assignments[info["key"]] = group_name
                        assigned_counts_by_field[field.id] += 1
                        currently_protecting += 1

            # If still less than half, we allow limited partial protection toward the next highest-threat field,
            # assigning closest unassigned drones until half is reached (this is a last-resort to satisfy "at least half protecting").
            if currently_protecting < half_needed:
                # pick the highest-threat field (could be the main field or others) for partial fill
                candidates = sorted(threatened_fields, key=lambda f: f.threat_level, reverse=True)
                # choose the top candidate that has group available
                partial_field = None
                for f in candidates:
                    if group_name_for(f) in group_ids:
                        partial_field = f
                        break
                if partial_field is not None:
                    group_name = group_name_for(partial_field)
                    unassigned_infos = [info for info in drone_infos if info["key"] not in assignments]
                    if unassigned_infos:
                        cx, cy = self._field_center(partial_field)
                        for info in unassigned_infos:
                            info.setdefault("distances", {})[partial_field.id] = self._distance(info["x"], info["y"], cx, cy)
                        # pick closest ones until we reach half_needed or until we've assigned up to field.drones_for_full_protection
                        max_allowed = int(getattr(partial_field, "drones_for_full_protection", half_needed))
                        currently_assigned_to_field = assigned_counts_by_field.get(partial_field.id, 0)
                        can_assign = min(max_allowed - currently_assigned_to_field, half_needed - currently_protecting)
                        if can_assign > 0:
                            sorted_candidates = sorted(unassigned_infos, key=lambda info: info["distances"][partial_field.id])
                            chosen = sorted_candidates[:can_assign]
                            for info in chosen:
                                assignments[info["key"]] = group_name
                                assigned_counts_by_field[partial_field.id] += 1
                                currently_protecting += 1

        # 4) Any remaining unassigned drones -> idle (if allowed), else assign them to main group if group exists
        for info in drone_infos:
            key = info["key"]
            if key in assignments:
                continue
            # default to idle if allowed
            if "idle" in group_ids:
                assignments[key] = "idle"
            else:
                # fallback: if main_group available, assign to it (should not happen in normal inputs)
                if main_group in group_ids:
                    assignments[key] = main_group
                else:
                    # else assign to first valid group_id
                    assignments[key] = group_ids[0] if group_ids else "idle"

        # 5) Apply assignments using environment.assign_group and update stability tracking
        for info in drone_infos:
            key = info["key"]
            comp = info["comp"]
            new_group = assignments.get(key, "idle")
            # Ensure we only assign groups that are in group_ids
            if new_group not in group_ids and "idle" in group_ids:
                new_group = "idle"
            environment.assign_group(comp, new_group)
            prev = self.prev_assignments.get(key)
            if prev == new_group:
                self.stable_steps[key] = self.stable_steps.get(key, 0) + 1
            else:
                self.stable_steps[key] = 0
            self.prev_assignments[key] = new_group