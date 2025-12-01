from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # memory: maps drone id to last field id it protected (or None if idle)
        self._drone_last_field = {}

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return (cx, cy)

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
        desired_group_map = {}

        # Phase 1: Top field
        top = fields_sorted[0]
        top_group = f"protecting {top.id}"
        req_top = int(getattr(top, "drones_for_full_protection", 0))
        current_top = len(current_protect.get(top.id, []))
        if current_top < req_top:
            need = req_top - current_top

            # Pool of movable drones:
            pool = []
            for cand in components:
                # Skip drones already protecting the top field
                if getattr(cand, "state", None) == "protecting" and getattr(cand, "target_id", None) == top.id:
                    continue

                movable = False
                if getattr(cand, "state", None) != "protecting":
                    movable = True
                else:
                    other_id = getattr(cand, "target_id", None)
                    if other_id is not None:
                        other_field = field_by_id.get(other_id)
                        if other_field is not None:
                            other_cur = len(current_protect.get(other_id, []))
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                movable = True
                if movable:
                    pool.append(cand)

            scored = []
            for cand in pool:
                last_match = (self._drone_last_field.get(id(cand)) == top.id)
                dist = self._dist_to_field(cand, top)
                scored.append((0 if last_match else 1, dist, cand))
            scored.sort()

            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                if top_group not in group_ids:
                    continue
                desired_group_map[cand] = top_group
                self._drone_last_field[id(cand)] = top.id
                assigned.add(cand)
                picked += 1

        # Phase 2: Other fields (without compromising top field)
        # Build updated current map after Phase 1 moves
        updated_current = {fid: list(lst) for fid, lst in current_protect.items()}
        # Remove any drones moved in Phase 1 from their previous fields
        for d in assigned:
            for fid in list(updated_current.keys()):
                lst = updated_current[fid]
                if d in lst:
                    lst.remove(d)
        # Add all Phase 1 drones to the top field
        updated_current[top.id] = updated_current.get(top.id, []) + list(assigned)

        # For each subsequent field, try to fully protect if possible
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            current_count = len(updated_current.get(f.id, []))
            if current_count >= req:
                continue
            need = req - current_count

            # Pool: avoid pulling from top field; allow idle or surplus drones
            pool = []
            for d in components:
                if d in assigned:
                    continue
                # Don't pull from top field
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
                            other_cur = len(updated_current.get(other_id, []))
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                movable = True
                        else:
                            movable = True
                    else:
                        movable = True
                if movable:
                    pool.append(d)

            scored = []
            for cand in pool:
                last_match = (self._drone_last_field.get(id(cand)) == f.id)
                dist = self._dist_to_field(cand, f)
                scored.append((0 if last_match else 1, dist, cand))
            scored.sort()

            picked = 0
            target_group = f"protecting {f.id}"
            for _, _, cand in scored:
                if picked >= need:
                    break
                if target_group not in group_ids:
                    continue
                desired_group_map[cand] = target_group
                self._drone_last_field[id(cand)] = f.id
                assigned.add(cand)
                picked += 1

        # Apply assignments
        for d, grp in desired_group_map.items():
            environment.assign_group(d, grp)

        # Drones not assigned go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None