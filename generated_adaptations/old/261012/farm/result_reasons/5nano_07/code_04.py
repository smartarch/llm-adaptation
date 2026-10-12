from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # memory: maps drone id to last field id it protected (or None if idle)
        self._drone_last_field = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, set all to idle
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None
            return

        # Sort fields by threat level (most threatened first)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Helpers
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

        # Current protectors per field
        current_protectors_by_field = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protectors_by_field.setdefault(t, []).append(d)

        # Desired allocations: mapping from drone -> target group
        desired_alloc = {}

        # Phase 1: fully protect the top threat field
        top_field = fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        current_top = current_protectors_by_field.get(top_field.id, [])
        if len(current_top) < required_top:
            need = required_top - len(current_top)

            # Candidates: drones not currently protecting the top field
            candidates = [
                d for d in components
                if d not in current_top and not (
                    getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
                )
            ]

            scored = []
            for cand in candidates:
                # score by continuity (prefer those who last protected the same field) and distance
                last_match = (self._drone_last_field.get(id(cand)) == top_field.id)
                dist = distance_to_field(cand, top_field)
                scored.append((0 if last_match else 1, dist, cand))

            scored.sort()
            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                # Assign to top field
                desired_alloc[cand] = top_group
                self._drone_last_field[id(cand)] = top_field.id
                picked += 1

        # Phase 2: other threatened fields (do not pull drones from the top field)
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            group = f"protecting {f.id}"
            required = int(getattr(f, "drones_for_full_protection", 0))
            current_list = current_protectors_by_field.get(f.id, [])
            # Include any drones already allocated to this field in Phase 1 as well
            current_list = [d for d in current_list if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id]
            current_count = len(current_list)

            if current_count >= required:
                continue

            need = required - current_count
            if need <= 0:
                continue

            # Candidates: avoid drones protecting the top field (to keep top field protected)
            candidates = [
                d for d in components
                if not (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id)
                and d not in current_list
            ]

            scored = []
            for cand in candidates:
                last_match = (self._drone_last_field.get(id(cand)) == f.id)
                dist = distance_to_field(cand, f)
                scored.append((0 if last_match else 1, dist, cand))
            scored.sort()
            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                desired_alloc[cand] = group
                self._drone_last_field[id(cand)] = f.id
                picked += 1

        # Assign all drones to their desired groups; if not specified, idle
        assigned = set(desired_alloc.keys())

        # Ensure groups exist for all protection targets
        for d, grp in desired_alloc.items():
            environment.assign_group(d, grp)

        # Drones not in desired_alloc -> idle (explicitly re-assign)
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None