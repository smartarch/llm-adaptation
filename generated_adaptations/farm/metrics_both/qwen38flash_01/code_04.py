import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        # --- Sort active fields by threat level descending ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # --- If no active threats, park all drones in idle group ---
        if not active_fields:
            for d in components:
                d.group = group_id
            return

        # --- Compute field centers ---
        centers = {}
        for f in environment.fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            centers[f.id] = (cx, cy)

        # --- Cache drone positions and current field assignments ---
        drone_pos = {}
        drone_current_fid = {}
        for d in components:
            drone_pos[d.id] = (d.location.x, d.location.y)
            drone_current_fid[d.id] = d.target_id if d.target_id is not None else None

        # --- Group drones by their current field for stickiness ---
        field_holders = {}  # field_id -> [drone_ids currently assigned there]
        for d in components:
            fid = drone_current_fid[d.id]
            if fid is not None:
                field_holders.setdefault(fid, []).append(d.id)

        # --- Greedy assignment in priority order ---
        assigned = set()       # drone ids that have been assigned to a field
        drone_to_field = {}    # drone_id -> field_id

        for f in active_fields:
            fid = f.id
            cx, cy = centers[fid]
            needed = f.drones_for_full_protection

            if needed <= 0:
                continue

            # Separate drones into those already here vs. elsewhere
            here = [did for did in field_holders.get(fid, []) if did not in assigned]
            elsewhere = [d.id for d in components if d.id not in assigned and d.id not in set(here)]

            # Sort each group by distance to this field center
            here.sort(key=lambda did: (drone_pos[did][0] - cx) ** 2 + (drone_pos[did][1] - cy) ** 2)
            elsewhere.sort(key=lambda did: (drone_pos[did][0] - cx) ** 2 + (drone_pos[did][1] - cy) ** 2)

            # Prefer already-here drones (stickiness), then closest others
            to_assign = here[:needed]
            remaining_slots = needed - len(to_assign)
            if remaining_slots > 0:
                to_assign.extend(elsewhere[:remaining_slots])

            # Assign
            for did in to_assign:
                drone_to_field[did] = fid
                assigned.add(did)

        # --- Apply assignments via group mechanism ---
        # Build a reverse lookup for efficiency
        field_group_names = {}
        for f in environment.fields:
            # Use the field's own group_id if available, otherwise str(field.id)
            if hasattr(f, 'group_id'):
                field_group_names[f.id] = str(f.group_id)
            else:
                field_group_names[f.id] = str(f.id)

        for d in components:
            fid = drone_to_field.get(d.id)
            if fid is not None:
                gname = field_group_names.get(fid, str(fid))
                d.group = gname
            else:
                d.group = group_id