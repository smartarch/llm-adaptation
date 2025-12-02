from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]

        # If no threatening fields, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        # Map field_id -> field object for quick lookup
        field_by_id = {f.id: f for f in threat_fields}

        # Precompute field centers for distance calculations
        centers = {
            f.id: (
                (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0,
                (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            )
            for f in threat_fields
        }

        # Current assignments: drone_index -> field_id
        drone_to_field = {}

        # Seed with drones already protecting a threat field
        for idx, d in enumerate(components):
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    drone_to_field[idx] = tid

        # Stage 1: Ensure top field is fully protected if possible
        top_field = threat_fields[0]
        top_id = top_field.id
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        if top_required < 0:
            top_required = 0

        # Current protectors for top field
        current_top = [idx for idx, fid in drone_to_field.items() if fid == top_id]
        current_top_count = len(current_top)

        if top_required > 0 and current_top_count < top_required:
            need = top_required - current_top_count
            cx, cy = centers[top_id]

            # Build candidate pool: drones not currently protecting the top field
            candidates = []
            for idx, d in enumerate(components):
                if idx in current_top:
                    continue
                # We will allow using any drone not already protecting the top field (even if protecting other fields)
                # Compute distance to top field center
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = dx * dx + dy * dy
                candidates.append((dist, idx))

            candidates.sort()
            for _, idx in candidates[:need]:
                drone_to_field[idx] = top_id
                current_top.append(idx)
                current_top_count += 1
                if current_top_count >= top_required:
                    break

        # Stage 2: Allocate remaining drones proportionally to other fields
        # Prepare remaining fields (excluding top field)
        remaining_fields = threat_fields[1:]  # could be empty
        if remaining_fields:
            # Current protectors per field
            current_counts = {f.id: 0 for f in remaining_fields}
            for idx, fid in drone_to_field.items():
                if fid in current_counts:
                    current_counts[fid] += 1

            # Remaining protection needs per field
            remaining_needs = {}
            sum_threat = 0.0
            for f in remaining_fields:
                req = int(getattr(f, "drones_for_full_protection", 0))
                if req < 0:
                    req = 0
                cur = current_counts.get(f.id, 0)
                need = max(0, req - cur)
                remaining_needs[f.id] = need
                sum_threat += getattr(f, "threat_level", 0.0)

            # If there is no need or no drones left, skip
            total_drones = len(components)
            used_drones = len(drone_to_field)
            remaining_drones = total_drones - used_drones
            if remaining_drones > 0 and sum(remaining_needs.values()) > 0:
                # Compute proportional allocations with exact rounding
                # We distribute remaining_drones among fields in proportion to their needs and threat
                # To keep it simple and stable, we use needs-based proportion first, then adjust to sum to remaining_drones.
                # Compute base quotas based on needs
                quotas = {}
                total_needs = sum(remaining_needs.values())
                # If total_needs == 0, skip
                if total_needs > 0:
                    # Raw quotas (real numbers)
                    raw = {}
                    for fid, need in remaining_needs.items():
                        raw_quota = (need / total_needs) * remaining_drones
                        raw[fid] = raw_quota

                    # Floor quotas and collect remainders for redistribution
                    floor_sum = 0
                    remainders = []
                    for fid, rq in raw.items():
                        q = int(rq)
                        quotas[fid] = q
                        floor_sum += q
                        remainders.append((rq - q, fid))

                    diff = remaining_drones - floor_sum
                    # Distribute the remaining by largest fractional parts
                    remainders.sort(reverse=True)
                    idx_r = 0
                    while diff > 0 and idx_r < len(remainders):
                        _, fid = remainders[idx_r]
                        quotas[fid] += 1
                        diff -= 1
                        idx_r += 1

                    # Cap quotas by remaining_needs so we never exceed
                    for fid in list(quotas.keys()):
                        quotas[fid] = min(quotas[fid], remaining_needs[fid])

                    # Now allocate drones to each field according to quotas
                    # Build a pool of candidates: drones not already protecting any field (to minimize disruption)
                    assigned_this_round = set([i for i in range(len(components)) if i in drone_to_field])
                    # We'll fill per field in order of threat (highest first among remaining_fields)
                    # Create a list of field ids sorted by threat
                    remaining_fields_sorted = sorted(remaining_fields, key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

                    for f in remaining_fields_sorted:
                        fid = f.id
                        quota = quotas.get(fid, 0)
                        if quota <= 0:
                            continue
                        # Distance center
                        cx, cy = centers[fid]
                        # Prepare candidates: drones not yet assigned to any field
                        candidates = []
                        for idx, d in enumerate(components):
                            if idx in drone_to_field:
                                continue
                            loc = getattr(d, "location", None)
                            if loc is None:
                                dist = float("inf")
                            else:
                                dx = loc.x - cx
                                dy = loc.y - cy
                                dist = dx * dx + dy * dy
                            candidates.append((dist, idx))
                        candidates.sort()
                        # Assign up to quota drones
                        assigned = 0
                        for _, idx in candidates:
                            if assigned >= quota:
                                break
                            drone_to_field[idx] = fid
                            assigned += 1

        # Final assignment: assign drones to their protected field groups, rest idle
        for i, d in enumerate(components):
            if i in drone_to_field:
                environment.assign_group(d, f"protecting {drone_to_field[i]}")
            else:
                environment.assign_group(d, "idle")