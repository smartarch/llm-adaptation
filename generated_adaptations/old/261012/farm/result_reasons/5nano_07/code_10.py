from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # memory: maps drone id to last field id it protected (or None if idle)
        self._drone_last_field = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist_to_field(self, drone, field):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        cx, cy = self._field_center(field)
        dx = loc.x - cx
        dy = loc.y - cy
        return (dx*dx + dy*dy) ** 0.5

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, set all drones to idle
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None
            return

        # Sort fields by threat level (most threatened first)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Build current protect map: field_id -> list of drones currently protecting it
        current_protect = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protect.setdefault(t, []).append(d)

        # Helper: map field_id -> field object
        field_by_id = {f.id: f for f in fields}

        assigned = set()

        # Phase 1: Top field
        top = fields_sorted[0]
        top_group = f"protecting {top.id}"
        req_top = int(getattr(top, "drones_for_full_protection", 0))
        cur_top = len(current_protect.get(top.id, []))
        if cur_top < req_top:
            need = req_top - cur_top

            # Build pool of movable drones
            pool = []
            for d in components:
                # Skip drones already protecting the top field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id:
                    continue

                movable = False
                if getattr(d, "state", None) != "protecting":
                    movable = True
                else:
                    other_id = getattr(d, "target_id", None)
                    if other_id is not None:
                        other_field = field_by_id.get(other_id)
                        if other_field is not None:
                            other_cur = len(current_protect.get(other_id, []))
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                movable = True
                if movable:
                    dist = self._dist_to_field(d, top)
                    last_match = (self._drone_last_field.get(id(d)) == top.id)
                    pool.append((dist, 0 if last_match else 1, d))
            pool.sort()
            if len(pool) >= need:
                picked = 0
                for dist, _, cand in pool:
                    if picked >= need:
                        break
                    if top_group not in group_ids:
                        continue
                    environment.assign_group(cand, top_group)
                    self._drone_last_field[id(cand)] = top.id
                    assigned.add(cand)
                    # Update current_protect map
                    old_id = getattr(cand, "target_id", None)
                    if getattr(cand, "state", None) == "protecting" and old_id is not None:
                        if cand in current_protect.get(old_id, []):
                            current_protect[old_id].remove(cand)
                    current_protect.setdefault(top.id, []).append(cand)
                    picked += 1

        # Phase 2: Remaining fields
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            current = len(current_protect.get(f.id, []))
            if current >= req:
                continue
            need = req - current

            pool = []
            for d in components:
                if d in assigned:
                    continue
                # avoid pulling from the top field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id:
                    continue

                movable = False
                if getattr(d, "state", None) != "protecting":
                    movable = True
                else:
                    other_id = getattr(d, "target_id", None)
                    if other_id is not None:
                        other_field = field_by_id.get(other_id)
                        if other_field is not None:
                            other_cur = len(current_protect.get(other_id, []))
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                movable = True
                        else:
                            movable = True
                    else:
                        movable = True
                if movable:
                    dist = self._dist_to_field(d, f)
                    last_match = (self._drone_last_field.get(id(d)) == f.id)
                    pool.append((dist, 0 if last_match else 1, d))
            pool.sort()
            if len(pool) >= need:
                picked = 0
                target_group = f"protecting {f.id}"
                for dist, _, cand in pool:
                    if picked >= need:
                        break
                    if target_group not in group_ids:
                        continue
                    environment.assign_group(cand, target_group)
                    self._drone_last_field[id(cand)] = f.id
                    assigned.add(cand)
                    old_id = getattr(cand, "target_id", None)
                    if getattr(cand, "state", None) == "protecting" and old_id is not None:
                        if cand in current_protect.get(old_id, []):
                            current_protect[old_id].remove(cand)
                    current_protect.setdefault(f.id, []).append(cand)
                    picked += 1

        # Final: idle everything not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None