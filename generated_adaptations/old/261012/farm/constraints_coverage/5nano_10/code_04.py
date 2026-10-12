from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper: field center
        def center(field):
            cx = (getattr(field, "left", 0.0) + getattr(field, "right", 0.0)) / 2.0
            cy = (getattr(field, "top", 0.0) + getattr(field, "bottom", 0.0)) / 2.0
            return cx, cy

        # Map field_id -> field object for quick access
        field_by_id = {f.id: f for f in threat_fields}

        # Initial allocation: drones currently protecting a field
        allocated_by_field = {f.id: [] for f in threat_fields}
        current_owner = {}  # drone_index -> field_id (only for protecting drones)
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in allocated_by_field:
                    allocated_by_field[tid].append(idx)
                    current_owner[idx] = tid

        # Determine required drones per field
        required_map = {}
        for f in threat_fields:
            req = getattr(f, "drones_for_full_protection", 1)
            if req < 0:
                req = 0
            required_map[f.id] = int(req)

        # Helper: distance from drone to field center
        def dist_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = center(f)
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return (dx * dx + dy * dy) ** 0.5

        # Process each field to fill needs, using donors (surplus or idle)
        for f in threat_fields:
            fid = f.id
            current_list = allocated_by_field.get(fid, [])
            need = max(0, required_map[fid] - len(current_list))
            if need == 0:
                continue

            # Build a list of potential donors:
            # - Drones currently protecting other fields with surplus (their field has more than its required)
            # - Idle drones (not currently protecting any field)
            donors = []
            # First, collect surplus protectors as donors
            for other_fid, lst in allocated_by_field.items():
                if other_fid == fid:
                    continue
                # skip if this field has no surplus
                if len(lst) > required_map.get(other_fid, 0):
                    # all drones in this list are potential donors, feel free to choose closest later
                    for idx in lst:
                        donors.append((idx, other_fid))

            # Idle drones: those not currently owned by any field
            for idx, d in enumerate(components):
                if idx in current_owner:
                    continue  # already protecting some field
                # Idle candidate
                donors.append((idx, None))

            # Deduplicate donors by index, keep the closest among duplicates later
            # Build a pool of candidate drones with distance to f
            candidate_pool = []
            for donor_idx, from_field in donors:
                # Skip if already allocated to this field
                if donor_idx in current_list:
                    continue
                # distance metric
                dist = dist_to_field(components[donor_idx], f)
                candidate_pool.append((dist, donor_idx, from_field))

            # Sort by distance and pick the closest 'need' donors
            candidate_pool.sort(key=lambda t: t[0])

            picked = []
            taken_indices = set(current_list)  # already protecting this field
            for dist, idx, from_field in candidate_pool:
                if len(picked) >= need:
                    break
                if idx in taken_indices:
                    continue
                picked.append((idx, from_field))

            # Apply picked donors: move them to this field
            for idx, from_field in picked:
                # If this drone was protecting another field, remove it from that field's list
                if from_field is not None and from_field in allocated_by_field:
                    if idx in allocated_by_field[from_field]:
                        allocated_by_field[from_field].remove(idx)
                # Assign to current field
                allocated_by_field fid = allocated_by_field.get(fid, [])
                allocated_by_field[fid].append(idx)
                current_owner[idx] = fid

        # After allocation, build final mapping: drone -> field (or None)
        drone_to_field = {}
        for f in threat_fields:
            for idx in allocated_by_field.get(f.id, []):
                drone_to_field[idx] = f.id

        # Final assignment: either protecting {field} or idle
        for idx, d in enumerate(components):
            field_id = drone_to_field.get(idx, None)
            if field_id is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, f"protecting {field_id}")