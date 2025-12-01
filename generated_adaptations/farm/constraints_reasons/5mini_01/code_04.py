from typing import List, Dict
from math import hypot
import math

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
        # If no drones, nothing to assign
        if not components:
            return

        # Identify threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields -> idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by descending threat, tie-break by id for determinism
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Precompute centers and capacities
        field_centers = {f.id: self._field_center(f) for f in threatened_fields}
        field_capacity = {f.id: max(0, int(getattr(f, "drones_for_full_protection", 0))) for f in threatened_fields}

        # Utility to get group name
        def grp(fid):
            return f"protecting {fid}"

        total_drones = len(components)
        min_protect = (total_drones + 1) // 2  # ceil half

        # Prepare containers
        planned: Dict[str, List] = {f.id: [] for f in threatened_fields}
        assigned_set = set()  # components already assigned to some planned list

        # Helper to preference value for stability
        def stability_pref(c, fid):
            state = getattr(c, "state", None)
            target = getattr(c, "target_id", None)
            # lower is better
            if state == "protecting" and target == fid:
                return 0
            if state == "moving_to_field" and target == fid:
                return 1
            if state == "idle" or target is None:
                return 2
            if state == "protecting":
                return 3
            return 4

        # 1) Ensure the top (most threatened) field is fully protected.
        main_field = threatened_fields[0]
        main_id = main_field.id
        main_cap = field_capacity.get(main_id, 0)
        # Build list of all drones sorted primarily by distance to main center, secondary by stability preference
        main_cx, main_cy = field_centers[main_id]
        all_sorted_for_main = sorted(
            components,
            key=lambda c: (self._dist(c.location, main_cx, main_cy), stability_pref(c, main_id))
        )
        # Choose top main_cap drones (or fewer if not enough drones exist)
        for c in all_sorted_for_main[:main_cap]:
            planned[main_id].append(c)
            assigned_set.add(c)

        # 2) For other fields, try to fully protect them using remaining drones.
        for f in threatened_fields[1:]:
            fid = f.id
            cap = field_capacity.get(fid, 0)
            if cap <= 0:
                continue
            # Prefer drones already protecting this field
            candidates = []
            # First prefer current protectors of this field
            for c in components:
                if c in assigned_set:
                    continue
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid:
                    candidates.append(c)
            # Then moving to this field
            for c in components:
                if c in assigned_set or c in candidates:
                    continue
                if getattr(c, "state", None) == "moving_to_field" and getattr(c, "target_id", None) == fid:
                    candidates.append(c)
            # Then remaining closest drones
            fid_cx, fid_cy = field_centers[fid]
            remaining_candidates = [c for c in components if c not in assigned_set and c not in candidates]
            remaining_candidates.sort(key=lambda c: self._dist(c.location, fid_cx, fid_cy))
            candidates.extend(remaining_candidates)
            # Take up to capacity
            take = candidates[:cap]
            for c in take:
                planned[fid].append(c)
                assigned_set.add(c)

        # 3) Ensure at least half the drones are protecting (if possible).
        assigned_protecting_count = sum(len(lst) for lst in planned.values())
        if assigned_protecting_count < min_protect:
            # Fill additional assignments to fields by descending threat, without exceeding capacities
            # For each field, compute remaining capacity
            for f in threatened_fields:
                if assigned_protecting_count >= min_protect:
                    break
                fid = f.id
                cap = field_capacity.get(fid, 0)
                remaining_cap = max(0, cap - len(planned[fid]))
                if remaining_cap <= 0:
                    continue
                # Choose closest remaining drones (prefer those moving to / idle)
                fid_cx, fid_cy = field_centers[fid]
                candidates = [c for c in components if c not in assigned_set]
                if not candidates:
                    break
                candidates.sort(key=lambda c: (stability_pref(c, fid), self._dist(c.location, fid_cx, fid_cy)))
                need = min(remaining_cap, min_protect - assigned_protecting_count)
                take = candidates[:need]
                for c in take:
                    planned[fid].append(c)
                    assigned_set.add(c)
                assigned_protecting_count = sum(len(lst) for lst in planned.values())

        # 4) Any unassigned drones -> idle
        assignment_map = {}
        for fid, lst in planned.items():
            gname = grp(fid)
            if gname not in group_ids:
                gname = "idle"
            for c in lst:
                assignment_map[c] = gname
        for c in components:
            if c not in assignment_map:
                assignment_map[c] = "idle"

        # 5) Apply assignments exactly once per component
        for c, g in assignment_map.items():
            environment.assign_group(c, g)