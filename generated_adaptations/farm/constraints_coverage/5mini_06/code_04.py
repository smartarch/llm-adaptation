from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that:
        - The field with the highest threat_level (>0) is fully protected with the closest drones.
        - Drones already moving_to_field or protecting a field are treated as committed to that field.
        - If fewer than half of drones are protecting after securing the highest-threat field,
          allocate additional drones to other threatened fields (by threat desc and proximity)
          until at least half the drones are protecting or no drones/fields remain.
        - All drones are explicitly assigned each call.
        """
        def _distance_to_field_center(comp, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = (getattr(comp.location, "x", 0.0) - cx)
            dy = (getattr(comp.location, "y", 0.0) - cy)
            return math.hypot(dx, dy)

        total_drones = len(components)
        if total_drones == 0:
            return

        # Collect fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: all idle
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort threatened fields by descending threat_level (tie: keep original order)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Build map of existing assigned drones per field (committed drones we won't reassign)
        committed = {}  # field.id -> list of components
        for f in threatened_fields:
            committed[f.id] = []
        for comp in components:
            tid = getattr(comp, "target_id", None)
            state = getattr(comp, "state", "")
            if tid is not None and state in ("moving_to_field", "protecting") and tid in committed:
                committed[tid].append(comp)

        # Desired minimum number of protecting drones (at least half)
        desired_protect = ceil(total_drones / 2)

        # Track which drones we decide to assign to protect groups
        assigned_to_protect = set()

        # Available candidate drones that are not committed to any field (idle or free)
        free_candidates = [c for c in components if not (getattr(c, "target_id", None) in committed and getattr(c, "state", "") in ("moving_to_field", "protecting"))]

        # Helper to safely get group name for a field and check validity
        def protect_group_name(field):
            name = f"protecting {field.id}"
            return name if name in group_ids else None

        # 1) Always ensure highest-threat field is fully protected with closest drones
        highest = threatened_fields[0]
        high_group = protect_group_name(highest)
        # If protecting group invalid, fallback to idle everyone (safe fallback)
        if high_group is None:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        required_high = max(0, int(getattr(highest, "drones_for_full_protection", 0)))
        # Start with committed drones for highest
        high_committed = list(committed.get(highest.id, []))
        for c in high_committed:
            assigned_to_protect.add(c)
        # Remove high_committed from free_candidates if present
        free_candidates = [c for c in free_candidates if c not in assigned_to_protect]

        need = max(0, required_high - len(high_committed))
        if need > 0 and free_candidates:
            # pick closest free_candidates to highest field
            free_candidates.sort(key=lambda c: _distance_to_field_center(c, highest))
            take = free_candidates[:need]
            for c in take:
                assigned_to_protect.add(c)
            # remove taken from free_candidates
            free_candidates = free_candidates[need:]

        # Also count other committed drones (they are protecting other fields already)
        for fid, comps in committed.items():
            if fid == highest.id:
                continue
            for c in comps:
                assigned_to_protect.add(c)

        # Count how many are protecting so far
        protecting_count = len(assigned_to_protect)

        # 2) If protecting_count < desired_protect, try to allocate to other fields
        # Iterate other fields by descending threat (skip highest)
        if protecting_count < desired_protect:
            for field in threatened_fields[1:]:
                if protecting_count >= desired_protect:
                    break
                group_name = protect_group_name(field)
                if group_name is None:
                    continue  # cannot assign to this field's group
                required = max(0, int(getattr(field, "drones_for_full_protection", 0)))
                already = len(committed.get(field.id, []))
                need_full = max(0, required - already)
                # if free_candidates is empty, break
                if not free_candidates:
                    break
                if need_full <= 0:
                    # field already fully protected by committed drones
                    # ensure those committed drones counted already (they were added)
                    continue
                # If not enough to fully satisfy need_full but we still require more to reach desired_protect,
                # assign as many as necessary (partial protection allowed to reach desired_protect)
                to_assign = min(need_full, len(free_candidates))
                # But we might need fewer than need_full to reach desired_protect
                extra_needed_to_half = desired_protect - protecting_count
                if extra_needed_to_half < to_assign:
                    to_assign = extra_needed_to_half
                # pick closest candidates to this field
                free_candidates.sort(key=lambda c: _distance_to_field_center(c, field))
                take = free_candidates[:to_assign]
                for c in take:
                    assigned_to_protect.add(c)
                # remove taken from free_candidates
                free_candidates = free_candidates[to_assign:]
                protecting_count = len(assigned_to_protect)
                # continue to next field if still under desired_protect

        # 3) Final assignment: assign drones in assigned_to_protect to appropriate field groups.
        # For drones that are committed to a specific field, prefer that field's group.
        # For drones we selected from free_candidates, we must know which field they were selected for.
        # To simplify, rebuild a mapping: for each field, determine the set of drones that should protect it:
        per_field_selected = {f.id: set() for f in threatened_fields}
        # fill with committed ones
        for fid, comps in committed.items():
            for c in comps:
                if c in assigned_to_protect:
                    per_field_selected[fid].add(c)
        # ensure highest gets its selected ones (in case some were free selected)
        # If some assigned_to_protect drones are not yet placed in per_field_selected (they were free selected),
        # place them greedily to the nearest threatened field whose group name is valid, favoring higher-threat order.
        unplaced = [c for c in assigned_to_protect if all(c not in s for s in per_field_selected.values())]
        if unplaced:
            # Try to place them to the fields we used allocation for: start with highest, then others by desc threat
            fields_order = threatened_fields.copy()
            for c in unplaced:
                placed = False
                # Try fields in order of proximity among fields_order, but prefer higher-threat first
                # Compute sorted fields by (threat_rank, distance)
                scored = []
                for idx, f in enumerate(fields_order):
                    name = protect_group_name(f)
                    if name is None:
                        continue
                    d = _distance_to_field_center(c, f)
                    scored.append((idx, d, f))
                if scored:
                    scored.sort(key=lambda x: (x[0], x[1]))  # prioritize by threat order then distance
                    chosen_field = scored[0][2]
                    per_field_selected[chosen_field.id].add(c)
                    placed = True
                if not placed:
                    # fallback: leave it unplaced; it'll be assigned to idle below
                    pass

        # Now assign groups:
        # - For each field, if group name valid, assign all drones in per_field_selected[field.id] to that group
        # - All other drones -> idle
        assigned_any = set()
        for field in threatened_fields:
            group = protect_group_name(field)
            if group is None:
                continue
            members = per_field_selected.get(field.id, set())
            for c in members:
                environment.assign_group(c, group)
                assigned_any.add(c)

        # Remaining drones -> idle
        for comp in components:
            if comp not in assigned_any:
                environment.assign_group(comp, "idle")