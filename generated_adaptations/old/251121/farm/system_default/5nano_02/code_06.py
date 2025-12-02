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

        # Order fields by threat level (highest first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        # Map field_id -> field object for quick lookup
        field_by_id = {f.id: f for f in threat_fields}

        # Precompute centers for distance calculations
        centers = {
            f.id: ((getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0,
                   (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0)
            for f in threat_fields
        }

        # Initialize mapping: drone_index -> field_id (or None)
        drone_to_field = {}

        # Seed with drones already protecting a threat field
        for idx, d in enumerate(components):
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    drone_to_field[idx] = tid

        # Process fields in priority order, reallocating as needed
        for f in threat_fields:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required < 0:
                required = 0

            # Current protectors for this field
            current = [idx for idx, field in drone_to_field.items() if field == fid]
            current_count = len(current)

            need = max(0, required - current_count)

            # If we still need drones, allocate the closest available ones
            cx, cy = centers[fid]
            while need > 0:
                best_idx = None
                best_dist = float("inf")

                for idx, d in enumerate(components):
                    if drone_to_field.get(idx) != fid:
                        # Candidate drone to reallocate
                        loc = getattr(d, "location", None)
                        if loc is None:
                            dist = float("inf")
                        else:
                            dx = loc.x - cx
                            dy = loc.y - cy
                            dist = dx * dx + dy * dy
                        if dist < best_dist:
                            best_dist = dist
                            best_idx = idx

                if best_idx is None:
                    # No more drones to allocate
                    break

                # Reallocate best_idx to this field
                drone_to_field[best_idx] = fid
                need -= 1

        # Final assignment: assign drones to their protected field groups, rest idle
        for i, d in enumerate(components):
            if i in drone_to_field:
                environment.assign_group(d, f"protecting {drone_to_field[i]}")
            else:
                environment.assign_group(d, "idle")