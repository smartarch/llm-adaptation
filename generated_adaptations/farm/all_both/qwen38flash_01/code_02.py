import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist_to_field(self, drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((drone.location.x - cx) ** 2 + (drone.location.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Determine active fields (threat > 0) sorted by threat descending
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not active_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        active_field_ids = set(f.id for f in active_fields)
        field_map = {f.id: f for f in active_fields}

        # Classify drones by their current effective assignment
        # A drone is "on" a field if state is 'protecting' or 'moving_to_field'
        # and target_id matches an active field
        drone_current_field = {}
        for comp in components:
            fid = None
            if comp.state in ("protecting", "moving_to_field"):
                if comp.target_id in active_field_ids:
                    fid = comp.target_id
            drone_current_field[id(comp)] = fid

        # Group currently-assigned drones by their field
        field_existing = {f.id: [] for f in active_fields}
        available_drones = []  # list of drone objects with no current field
        for comp in components:
            fid = drone_current_field[id(comp)]
            if fid is not None:
                field_existing[fid].append(comp)
            else:
                available_drones.append(comp)

        # Build assignments dict: field_id -> list of drones assigned
        assignments = {f.id: [] for f in active_fields}

        # --- STEP 1: Determine how many drones each field wants ---
        # For the top-threat field, we MUST fully protect with closest drones.
        # For other fields, only protect if we CAN fully protect (or keep existing).

        # First, for the top field, gather ALL drones (existing + available) sorted by distance
        # and pick the closest N needed. This may steal from other fields.
        top_field = active_fields[0]
        top_needed = top_field.drones_for_full_protection

        # Collect all drones (from any field or idle) sorted by distance to top field
        all_drones = list(components)
        all_drones.sort(key=lambda d: self._dist_to_field(d, top_field))
        top_assign = all_drones[:top_needed]
        assignments[top_field.id] = top_assign
        top_assign_set = set(id(d) for d in top_assign)

        # Remove top-field drones from other field_existing and available pools
        for fid in field_existing:
            field_existing[fid] = [d for d in field_existing[fid] if id(d) not in top_assign_set]
        available_drones = [d for d in available_drones if id(d) not in top_assign_set]

        # --- STEP 2: For remaining fields (in threat order), assign drones ---
        # Prefer drones already on the field (stability), then closest available
        remaining_fields = active_fields[1:]

        for field in remaining_fields:
            fid = field.id
            needed = field.drones_for_full_protection
            if needed <= 0:
                continue

            # Drones already on this field (not stolen by top field)
            already_here = field_existing[fid]

            if len(already_here) >= needed:
                # Fully covered (or over) -> keep only 'needed' closest, excess -> available
                already_here.sort(key=lambda d: self._dist_to_field(d, field))
                keep = already_here[:needed]
                excess = already_here[needed:]
                assignments[fid] = keep
                available_drones.extend(excess)
            else:
                # Not enough on this field; can we reach full protection with available?
                still_needed = needed - len(already_here)
                if len(available_drones) >= still_needed:
                    # Pick closest available to this field
                    avail_sorted = sorted(available_drones, key=lambda d: self._dist_to_field(d, field))
                    to_add = avail_sorted[:still_needed]
                    assignments[fid] = already_here + to_add
                    to_add_set = set(id(d) for d in to_add)
                    available_drones = [d for d in available_drones if id(d) not in to_add_set]
                else:
                    # Cannot fully protect -> prefer not to partially protect.
                    # But keep drones already here for stability (they're already there).
                    assignments[fid] = already_here
                    # Don't send new available drones here (partial not effective)

        # --- STEP 3: Ensure at least half drones are active ---
        total = len(components)
        assigned_count = sum(len(v) for v in assignments.values())
        min_active = total // 2 + (1 if total % 2 else 0)  # ceiling of half

        if assigned_count < min_active and available_drones:
            # Try to fill under-protected fields with available drones
            for field in remaining_fields:
                if not available_drones:
                    break
                fid = field.id
                cap = field.drones_for_full_protection
                current = len(assignments[fid])
                gap = cap - current
                if gap <= 0:
                    continue
                take = min(gap, len(available_drones))
                avail_sorted = sorted(available_drones, key=lambda d: self._dist_to_field(d, field))
                to_add = avail_sorted[:take]
                assignments[fid].extend(to_add)
                to_add_set = set(id(d) for d in to_add)
                available_drones = [d for d in available_drones if id(d) not in to_add_set]
                assigned_count += take
                if assigned_count >= min_active:
                    break

        # --- STEP 4: Execute assignments ---
        # Track which drones we've assigned to avoid double-assignment
        handled = set()

        for field in active_fields:
            fid = field.id
            group_name = f"protecting {fid}"
            if group_name not in group_ids:
                continue
            for comp in assignments[fid]:
                environment.assign_group(comp, group_name)
                handled.add(id(comp))

        # All remaining -> idle
        for comp in components:
            if id(comp) not in handled:
                environment.assign_group(comp, "idle")