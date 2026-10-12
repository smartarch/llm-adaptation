from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # memory: maps drone id to last field id it protected (or None if idle)
        self._drone_last_field = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, keep all drones idle
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None
            return

        # Sort fields by threat level (most threatened first)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Map of current protectors per field (drones already protecting a field)
        current_protectors = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protectors.setdefault(t, []).append(d)

        # Candidate pool: drones not currently protecting any field
        candidates = [d for d in components if getattr(d, "state", None) != "protecting"]
        assigned = set()

        # Helper to compute Euclidean distance from drone to a field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        def distance_to_field(drone, field):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            cx, cy = field_center(field)
            dx = loc.x - cx
            dy = loc.y - cy
            return (dx*dx + dy*dy) ** 0.5

        # Allocate drones to fully protect fields, highest threat first
        available = len(candidates)

        for f in fields_sorted:
            if getattr(f, "threat_level", 0) <= 0:
                continue

            required = getattr(f, "drones_for_full_protection", 0)
            if not isinstance(required, int) or required <= 0:
                continue

            current = len(current_protectors.get(f.id, []))
            if current >= required:
                continue

            need = int(required) - current
            if need <= 0:
                continue

            # If we don't have enough available drones to fully protect this field, skip
            if need > available:
                continue

            # Center for distance computations
            center = field_center(f)

            d_id = lambda drone: id(drone)

            # Prepare candidates with scoring: prefer drones that last protected the same field,
            # then by distance to the field
            scored = []
            for cand in candidates:
                # Skip drones currently protecting another field
                if getattr(cand, "state", None) == "protecting":
                    continue
                last_match = 1 if self._drone_last_field.get(d_id(cand)) == f.id else 0
                dist = distance_to_field(cand, f)
                scored.append((-last_match, dist, cand))

            # Sort by: best last-field retention, then closest
            scored.sort()

            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                if cand in assigned:
                    continue
                group = f"protecting {f.id}"
                if group in group_ids:
                    environment.assign_group(cand, group)
                    assigned.add(cand)
                    self._drone_last_field[id(cand)] = f.id
                    candidates.remove(cand)
                    picked += 1
                    available -= 1

            # If we couldn't allocate the full need due to lack of suitable candidates, we skip this field
            # to avoid partial protection across multiple fields.

        # Remaining drones become idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None