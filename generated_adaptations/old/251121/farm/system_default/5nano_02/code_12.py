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

        # Determine threat ranks: 0 = highest, 1 = next, ...
        threat_ranks = {f.id: i for i, f in enumerate(threat_fields)}

        # Mapping: drone_index -> field_id (only for fields we may protect)
        drone_to_field = {}

        # Seed with drones already protecting a threat field
        for idx, d in enumerate(components):
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    drone_to_field[idx] = tid

        # Stage: allocate/protect fields in priority order
        for f in threat_fields:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required < 0:
                required = 0

            # Current protectors for this field
            current = [idx for idx, ft in drone_to_field.items() if ft == fid]
            current_count = len(current)

            if current_count >= required:
                continue  # already fully protected (or cannot be protected more)

            need = required - current_count
            if need <= 0:
                continue

            cx, cy = centers[fid]

            # Build candidate pool: drones not currently protecting this field
            # Allow reallocation only from lower-priority fields or idle
            candidates = []
            for idx, d in enumerate(components):
                if drone_to_field.get(idx) == fid:
                    continue
                curr_assigned = drone_to_field.get(idx)
                # Determine if we may reallocate from curr_assigned:
                # - If curr_assigned is None (idle): allowed
                # - If curr_assigned is a lower-priority field (its rank > current field's rank): allowed
                # - If curr_assigned is a higher-priority field (rank < current): not allowed
                if curr_assigned is not None:
                    if threat_ranks.get(curr_assigned, 999) <= threat_ranks.get(fid, 999):
                        # Curr assigned to equal or higher priority field -> do not pull
                        continue

                # Compute distance to this field center
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = dx * dx + dy * dy
                candidates.append((dist, idx))

            candidates.sort()
            # Allocate the closest drones up to 'need'
            for _, idx in candidates[:need]:
                drone_to_field[idx] = fid

        # Final assignment: assign drones to their protected field groups, rest idle
        for i, d in enumerate(components):
            if i in drone_to_field:
                environment.assign_group(d, f"protecting {drone_to_field[i]}")
            else:
                environment.assign_group(d, "idle")