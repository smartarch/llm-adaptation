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

        # Map: field_id -> set of drones assigned to protect that field
        assigned = {f.id: set() for f in threat_fields}

        # Precompute field centers for distance calculations
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in threat_fields}

        # Process fields in priority order
        for f in threat_fields:
            fid = f.id
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required < 0:
                required = 0

            # Drones currently protecting this field
            current = [i for i, d in enumerate(components)
                       if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            current_set = set(current)

            # Ensure current protectors are considered assigned for this field
            assigned[fid].update(current_set)

            current_count = len(current)
            if required == 0 or current_count >= required:
                # Already fully protected (or cannot be protected), skip adding more
                continue

            need = required - current_count

            # Build candidate pool: drones not already assigned to any field
            used = set().union(*assigned.values())
            cx, cy = centers[fid]
            candidates = []
            for idx, d in enumerate(components):
                if idx in used:
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
            for _, idx in candidates[:need]:
                assigned[fid].add(idx)

        # Compile final assignment: assign drones to their respective protection groups, others idle
        # Build a lookup from drone idx -> field id to minimize per-drone work
        drone_to_field = {}
        for fid, s in assigned.items():
            for idx in s:
                drone_to_field[idx] = fid

        for i, d in enumerate(components):
            if i in drone_to_field:
                environment.assign_group(d, f"protecting {drone_to_field[i]}")
            else:
                environment.assign_group(d, "idle")