from typing import Dict, Tuple
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map from id(component) -> (group_name, last_changed_step)
        self.prev_group_by_drone: Dict[int, Tuple[str, int]] = {}

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist2(self, x1, y1, x2, y2):
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build allowed protecting group names for fields with threat>0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not components:
            return  # nothing to assign

        # Map field id -> field object
        field_by_id = {f.id: f for f in fields}

        # All drones count
        all_drones = list(components)
        N = len(all_drones)
        half_needed = (N + 1) // 2  # ceil(N/2)

        # Precompute centers and drones_for_full_protection
        field_centers = {f.id: self._field_center(f) for f in fields}
        drones_needed_by_field = {f.id: int(getattr(f, "drones_for_full_protection", 1)) for f in fields}

        # Helper to compute distance squared between drone and field center
        def dist2_to_field(drone, field_id):
            cx, cy = field_centers[field_id]
            loc = getattr(drone, "location", None)
            if not loc:
                return float("inf")
            return self._dist2(loc.x, loc.y, cx, cy)

        # Build current targeting groups for drones (based on observed state/target_id).
        # Use group name "protecting {id}" for drones whose target_id matches a threatened field.
        current_observed_group = {}
        for d in all_drones:
            gid = "idle"
            tid = getattr(d, "target_id", None)
            st = getattr(d, "state", None)
            if tid is not None and tid in field_by_id:
                # If drone is moving_to_field or protecting or targeting a threatened field, consider it previously assigned there
                if st in ("moving_to_field", "protecting"):
                    gid = f"protecting {tid}"
                else:
                    # Even if not in those states, but target set to valid threatened field, treat as that group
                    gid = f"protecting {tid}"
            else:
                gid = "idle"
            current_observed_group[id(d)] = gid

        # Build pool of drones available for assignment
        drones_pool = set(all_drones)

        # Sort fields by threat descending, tie-breaker smaller drones_for_full_protection first
        fields_sorted = sorted(fields, key=lambda f: (-f.threat_level, drones_needed_by_field[f.id]))

        # Result assignment mapping id(d) -> group_name
        assignment = {}

        # Helper: pick K drones for a field, preferring those already targeting that field (to reduce churn),
        # then the closest remaining drones.
        def pick_drones_for_field(field_id, K, pool):
            picked = []
            # 1) take drones from pool that currently are observed targeting/protecting this field
            for d in list(pool):
                if current_observed_group.get(id(d), "idle") == f"protecting {field_id}":
                    picked.append(d)
                    pool.remove(d)
                    if len(picked) >= K:
                        return picked
            # 2) take closest remaining
            remaining = list(pool)
            remaining.sort(key=lambda d: dist2_to_field(d, field_id))
            for d in remaining:
                picked.append(d)
                pool.remove(d)
                if len(picked) >= K:
                    break
            return picked

        # 1) Always fully protect the most threatened field
        protected_count = 0
        protected_fields = set()
        if fields_sorted:
            top_field = fields_sorted[0]
            top_id = top_field.id
            K = max(0, int(drones_needed_by_field[top_id]))
            # Ensure we do not select more than available
            K = min(K, N)
            selected_for_top = pick_drones_for_field(top_id, K, drones_pool)
            # If fewer than K available (shouldn't happen), we still assign what we can.
            for d in selected_for_top:
                assignment[id(d)] = f"protecting {top_id}"
            protected_count += len(selected_for_top)
            if len(selected_for_top) > 0:
                protected_fields.add(top_id)

        # 2) Try to fully protect other fields (descending threat) using remaining drones
        for f in fields_sorted[1:]:
            fid = f.id
            K = int(drones_needed_by_field[fid])
            if K <= 0:
                continue
            # If not enough drones left to fully protect, skip for now
            if len(drones_pool) >= K:
                selected = pick_drones_for_field(fid, K, drones_pool)
                for d in selected:
                    assignment[id(d)] = f"protecting {fid}"
                if selected:
                    protected_fields.add(fid)
                protected_count += len(selected)
            # else leave for possible partial assignment to meet half-used requirement

        # 3) Ensure at least half of drones are used for protection; if not, allocate additional drones
        if protected_count < half_needed:
            # Determine remaining highest-priority field to put extra drones into (prefer next-highest threat)
            # Start from top field first (if it wasn't filled to its required K), else reuse the next fields sorted
            # Build a list of candidate fields in order (fields_sorted)
            for f in fields_sorted:
                fid = f.id
                max_allowed = int(drones_needed_by_field[fid])
                # Count how many already assigned to this field in assignment
                assigned_here = sum(1 for k, g in assignment.items() if g == f"protecting {fid}")
                can_add = max(0, max_allowed - assigned_here)
                if can_add <= 0:
                    continue
                need = half_needed - protected_count
                take = min(can_add, need, len(drones_pool))
                if take <= 0:
                    continue
                # pick closest remaining drones (prefer those currently observed targeting this field)
                selected = pick_drones_for_field(fid, take, drones_pool)
                for d in selected:
                    assignment[id(d)] = f"protecting {fid}"
                protected_count += len(selected)
                if protected_count >= half_needed:
                    break

        # 4) If still fewer than half (e.g., not enough full slots to add), allow partial assignment to the highest-threat field
        if protected_count < half_needed and fields_sorted:
            # choose highest-threat field (top_field) to receive partial defenders up to half_needed
            target_field = fields_sorted[0]
            fid = target_field.id
            max_allowed = int(drones_needed_by_field[fid])
            assigned_here = sum(1 for k, g in assignment.items() if g == f"protecting {fid}")
            can_add = max(0, max_allowed - assigned_here)
            need = half_needed - protected_count
            # If can_add is zero (already maxed), find next field with space or allow partial beyond max_allowed?
            # We will allow up to max_allowed so if no space anywhere we cannot reach half_used.
            if can_add > 0:
                take = min(can_add, need, len(drones_pool))
                if take > 0:
                    selected = pick_drones_for_field(fid, take, drones_pool)
                    for d in selected:
                        assignment[id(d)] = f"protecting {fid}"
                    protected_count += len(selected)

        # 5) Assign remaining drones: try to assign them to other fields if we have spare capacity for full protection
        # (to avoid too many idle drones), but prefer not to overprotect any field.
        for f in fields_sorted:
            fid = f.id
            max_allowed = int(drones_needed_by_field[fid])
            assigned_here = sum(1 for k, g in assignment.items() if g == f"protecting {fid}")
            can_add = max(0, max_allowed - assigned_here)
            if can_add <= 0:
                continue
            # fill as many as possible but don't drop below half_needed constraint
            take = min(can_add, len(drones_pool))
            if take <= 0:
                continue
            selected = pick_drones_for_field(fid, take, drones_pool)
            for d in selected:
                assignment[id(d)] = f"protecting {fid}"
            protected_count += len(selected)
            if not drones_pool:
                break

        # 6) Remaining drones -> idle
        for d in list(drones_pool):
            assignment[id(d)] = "idle"
            drones_pool.remove(d)

        # 7) Now perform the actual assignments via environment.assign_group and update previous assignment tracking.
        for d in all_drones:
            drone_key = id(d)
            grp = assignment.get(drone_key, "idle")
            # Safety: only assign groups that are in group_ids (allowed groups)
            if grp not in group_ids:
                # If desired protecting group not allowed (e.g., field no longer threatened), fallback to idle
                if "idle" in group_ids:
                    grp = "idle"
                else:
                    # fallback to the first allowed group
                    grp = group_ids[0] if group_ids else "idle"
            # Call the environment assign
            try:
                environment.assign_group(d, grp)
            except Exception:
                # Best-effort: ignore assignment failures to avoid crashing adaptation
                pass

            # Update prev tracking
            prev = self.prev_group_by_drone.get(drone_key)
            if prev is None:
                # New record
                self.prev_group_by_drone[drone_key] = (grp, step)
            else:
                prev_grp, prev_step = prev
                if prev_grp != grp:
                    self.prev_group_by_drone[drone_key] = (grp, step)
                else:
                    # no change; keep the old last_changed_step
                    self.prev_group_by_drone[drone_key] = (prev_grp, prev_step)