from generated_adaptations.base_classes.farm import FarmAdaptation
import math

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

        # Build mapping: current protectors per field (by field id)
        current_protect = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t is not None:
                    current_protect.setdefault(t, []).append(d)

        # Helper to get a field by id (from fields list)
        field_by_id = {f.id: f for f in fields}

        # Phase 1: Ensure the top-threat field is fully protected
        top_field = fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        req_top = int(getattr(top_field, "drones_for_full_protection", 0))
        cur_top = len(current_protect.get(top_field.id, []))
        desired_alloc = {}

        if cur_top < req_top:
            need = req_top - cur_top

            # Pool of movable drones:
            # - Idle drones
            # - Drones protecting other fields that can spare (i.e., that field has current > required)
            pool = []
            for d in components:
                # Drones already protecting the top field are already counted; skip them
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue

                movable = False
                if getattr(d, "state", None) != "protecting":
                    movable = True
                else:
                    # Currently protecting some other field; check if that field can spare a drone
                    other_id = getattr(d, "target_id", None)
                    if other_id is not None:
                        other_cur = len(current_protect.get(other_id, []))
                        other_field = field_by_id.get(other_id, None)
                        if other_field is not None:
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                movable = True
                if movable:
                    pool.append(d)

            # Score pool by continuity (prefer last_field == top_field) and distance
            scored = []
            for cand in pool:
                last_match = (self._drone_last_field.get(id(cand)) == top_field.id)
                dist = self._dist_to_field(cand, top_field)
                # We want to prioritize last_match, then closer distance
                scored.append((0 if last_match else 1, dist, cand))
            scored.sort()

            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                # Avoid assigning to a group that doesn't exist in group_ids
                if top_group not in group_ids:
                    continue
                desired_alloc[cand] = top_group
                self._drone_last_field[id(cand)] = top_field.id
                picked += 1

        # Phase 2: Protect subsequent fields as possible without compromising the top field
        # Recompute current protectors for decisions
        # (We rely on current_protect mapping, but it may be outdated for drones moved in Phase 1.
        # We'll approximate by considering drones already allocated in desired_alloc as now assigned to top_field.)
        assigned_now = set(desired_alloc.keys())
        # Update devilish case: if some drones in desired_alloc were protecting other fields before,
        # that field's current count should be reduced. We won't attempt a perfect dynamic update;
        # we will simply avoid pulling drones from the top field and from any field that would go below full.

        # Build a set of fields' current counts after Phase 1 rough update
        # We'll assume drones in desired_alloc have moved away from their previous fields.
        updated_current = {}
        for d in components:
            if d in assigned_now:
                # assigned to top_field
                pass
            else:
                # keep previous accounting
                if getattr(d, "state", None) == "protecting":
                    t = getattr(d, "target_id", None)
                    if t is not None:
                        updated_current.setdefault(t, []).append(d)

        # For each subsequent field, fill if possible
        for f in fields_sorted[1:]:
            if getattr(f, "threat_level", 0) <= 0:
                continue
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            current = len(updated_current.get(f.id, []))
            if current >= req:
                continue
            need = req - current

            # Pool candidates: do not pull from top_field; avoid breaking its protection
            pool = []
            for d in components:
                if d in assigned_now:
                    continue
                # Cannot pull from top field
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                if getattr(d, "state", None) == "protecting":
                    other_id = getattr(d, "target_id", None)
                    if other_id is not None:
                        other_cur = len(updated_current.get(other_id, []))
                        other_field = field_by_id.get(other_id, None)
                        if other_field is not None:
                            other_req = int(getattr(other_field, "drones_for_full_protection", 0))
                            if other_cur > other_req:
                                pool.append(d)
                        else:
                            pool.append(d)
                    else:
                        pool.append(d)
                else:
                    pool.append(d)

            scored = []
            for cand in pool:
                last_match = (self._drone_last_field.get(id(cand)) == f.id)
                dist = self._dist_to_field(cand, f)
                scored.append((0 if last_match else 1, dist, cand))
            scored.sort()

            picked = 0
            for _, _, cand in scored:
                if picked >= need:
                    break
                if f"{f.id}" is None:
                    continue
                group = f"protecting {f.id}"
                if group not in group_ids:
                    continue
                desired_alloc[cand] = group
                self._drone_last_field[id(cand)] = f.id
                picked += 1

        # Apply assignments
        assigned = set(desired_alloc.keys())
        for d, grp in desired_alloc.items():
            environment.assign_group(d, grp)

        # Remaining drones -> idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")
                self._drone_last_field[id(d)] = None