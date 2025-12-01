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
        field_by_id = {f.id: f for f in fields}
        costs = {f.id: int(getattr(f, "drones_for_full_protection", 0)) for f in fields}

        # Build current protect map: field_id -> list of drones currently protecting it
        current_protect = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protect.setdefault(t, []).append(d)

        assigned = set()

        # Phase 1: Top field
        top = fields_sorted[0]
        top_group = f"protecting {top.id}"
        req_top = costs[top.id]
        cur_top = len(current_protect.get(top.id, []))

        if cur_top < req_top:
            need = req_top - cur_top

            # Pool of movable drones
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
                    other_field = field_by_id.get(other_id)
                    if other_field is not None:
                        other_cur = len(current_protect.get(other_id, []))
                        other_req = costs.get(other_id, 0)
                        if other_cur > other_req:
                            movable = True
                    else:
                        # If the other field isn't tracked, treat as movable
                        movable = True

                if movable:
                    dist = self._dist_to_field(cand, top)
                    last_match = (self._drone_last_field.get(id(cand)) == top.id)
                    pool.append((dist, 0 if last_match else 1, cand))
            pool.sort()

            picked = 0
            for dist, _, cand in pool:
                if picked >= need:
                    break
                if top_group not in group_ids:
                    continue
                environment.assign_group(cand, top_group)
                self._drone_last_field[id(cand)] = top.id
                assigned.add(cand)
                # Update current_protect to reflect this move
                old_id = getattr(cand, "target_id", None)
                if getattr(cand, "state", None) == "protecting" and old_id is not None:
                    if cand in current_protect.get(old_id, []):
                        current_protect[old_id].remove(cand)
                current_protect.setdefault(top.id, []).append(cand)
                picked += 1

        # Phase 2: Remaining fields
        # Build updated current protect map after Phase 1 moves
        updated_current = {fid: list(lst) for fid, lst in current_protect.items()}
        if top.id not in updated_current:
            updated_current[top.id] = []
        for d in assigned:
            if d not in updated_current[top.id]:
                updated_current[top.id].append(d)

        # Pool of movable drones for other fields (excluding those assigned in Phase 1)
        pool2 = []
        for d in components:
            if d in assigned:
                continue
            # Do not pull from the top field
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id:
                continue

            movable = False
            if getattr(d, "state", None) != "protecting":
                movable = True
            else:
                other_id = getattr(d, "target_id", None)
                other_field = field_by_id.get(other_id)
                if other_field is not None:
                    other_cur = len(updated_current.get(other_id, []))
                    other_req = costs.get(other_id, 0)
                    if other_cur > other_req:
                        movable = True
                else:
                    movable = True
            if movable:
                pool2.append(d)

        # Determine remaining fields to protect (excluding top)
        remaining_fields = []
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            req = costs.get(f.id, 0)
            if req <= 0:
                continue
            current = len(updated_current.get(f.id, []))
            if current < req:
                remaining_fields.append((f, current, req))

        # Sort by threat density: threat_level / drones_for_full_protection
        remaining_fields.sort(key=lambda t: t[0].threat_level / max(1, int(costs.get(t[0].id, 0))), reverse=True)

        for f, current, req in remaining_fields:
            need = req - current
            if need <= 0:
                continue

            # Collect candidates from pool2 not yet assigned
            candidates_for_field = []
            for cand in pool2:
                if cand in assigned:
                    continue
                candidates_for_field.append(cand)

            if len(candidates_for_field) < need:
                # Not enough to fully protect this field; skip to avoid partial protection here
                continue

            # Score candidates for this field by distance, then continuity
            scored = []
            for cand in candidates_for_field:
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
                environment.assign_group(cand, target_group)
                self._drone_last_field[id(cand)] = f.id
                assigned.add(cand)
                # Update updated_current
                updated_current.setdefault(f.id, []).append(cand)
                # Remove from pool2
                if cand in pool2:
                    pool2.remove(cand)
                picked += 1

        # Final: idle everything not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None