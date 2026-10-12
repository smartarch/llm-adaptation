from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        def protecting_group(field_id):
            return f"protecting {field_id}"

        idle_group = "idle"
        speed = 2.0  # drone speed

        # Helpers
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_sq(ax, ay, bx, by):
            dx = ax - bx
            dy = ay - by
            return dx * dx + dy * dy

        def eta_from_loc_to(loc, tx, ty):
            if loc is None:
                return float("inf")
            d = math.sqrt(dist_sq(loc.x, loc.y, tx, ty))
            return d / speed

        # Collect threatened fields (threat_level > 0)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats: idle everything
            for c in components:
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
            return

        # Deterministic ordering: highest threat, tie-break by id
        fields_sorted = sorted(fields, key=lambda f: (-f.threat_level, str(f.id)))
        top_field = fields_sorted[0]
        top_cx, top_cy = field_center(top_field)

        # Map current assignments: field_id -> list of drones
        assigned_to_field = {f.id: [] for f in fields}
        for c in components:
            tid = getattr(c, "target_id", None)
            if tid in assigned_to_field:
                assigned_to_field[tid].append(c)

        # Identify fully protected fields and lock their drones
        fully_protected = set()
        for f in fields:
            req = getattr(f, "drones_for_full_protection", 0)
            if len(assigned_to_field.get(f.id, [])) >= req:
                fully_protected.add(f.id)

        locked_drones = set()
        locked_map = {}
        for fid in fully_protected:
            for c in assigned_to_field.get(fid, []):
                locked_drones.add(c)
                locked_map[c] = fid

        # Prepare decided assignments
        decided = {}

        # Keep locked drones at their fields
        for c in locked_drones:
            decided[c] = protecting_group(locked_map[c])

        # Count current assignments per field
        assigned_counts = {f.id: len(assigned_to_field.get(f.id, [])) for f in fields}

        # Stage 1: Fully protect top field
        top_req = getattr(top_field, "drones_for_full_protection", 0)
        top_current = len(assigned_to_field.get(top_field.id, []))
        need_top = max(0, top_req - top_current)

        # Keep drones already targeting top_field
        for c in assigned_to_field.get(top_field.id, []):
            decided[c] = protecting_group(top_field.id)

        # If we need extra drones, choose fastest-arriving unlocked drones, preferring idle/moving slightly
        if need_top > 0:
            candidates = [c for c in components if c not in locked_drones and getattr(c, "target_id", None) != top_field.id]
            scored = []
            for c in candidates:
                loc = getattr(c, "location", None)
                eta = eta_from_loc_to(loc, top_cx, top_cy)
                # small bias: idle/moving favored over protecting
                state = getattr(c, "state", "")
                state_bias = 0.0
                if state == "idle":
                    state_bias = -0.01
                elif state == "moving_to_field":
                    state_bias = -0.005
                # compute distance for tie-break
                d2 = dist_sq(loc.x, loc.y, top_cx, top_cy) if loc is not None else float("inf")
                scored.append((eta + state_bias, eta, d2, c))
            scored.sort(key=lambda t: (t[0], t[1], t[2]))
            chosen = [t[3] for t in scored[:need_top]]
            for c in chosen:
                decided[c] = protecting_group(top_field.id)
                # if c was counted in another field, decrement its assigned_counts (we won't pull from locked ones)
                tid = getattr(c, "target_id", None)
                if tid in assigned_counts:
                    assigned_counts[tid] = max(0, assigned_counts.get(tid, 0) - 1)

        # Stage 2: Opportunistically fully protect other fields if possible without harming partially protected ones
        # Build remaining pool: drones not locked and not already decided
        remaining = [c for c in components if c not in decided and c not in locked_drones]

        # Recompute current counts reflecting decided moves for top
        current_counts = {}
        for f in fields:
            lst = []
            for c in assigned_to_field.get(f.id, []):
                # If this drone was decided to move to top, it's no longer counted for this field
                if c in decided and decided[c] == protecting_group(top_field.id):
                    continue
                # locked drones on this field are kept (they were set in decided above)
                if c in locked_drones:
                    if locked_map.get(c) == f.id:
                        lst.append(c)
                    continue
                # if c not in decided it remains
                if c not in decided:
                    lst.append(c)
            current_counts[f.id] = len(lst)
        # also include decided protecting assignments beyond current lists
        for c, g in decided.items():
            if g.startswith("protecting "):
                fid_str = g[len("protecting "):]
                for key in list(current_counts.keys()):
                    if str(key) == str(fid_str):
                        if c not in assigned_to_field.get(key, []):
                            current_counts[key] = current_counts.get(key, 0) + 1

        # Helper to pick best k drones for a field from a pool:
        # prefer idle/moving, then drones from surplus fields, sorted by ETA
        def pick_best_for_field(field_obj, pool, k):
            tx, ty = field_center(field_obj)
            candidates = []
            for c in pool:
                state = getattr(c, "state", "")
                state_rank = 0 if state == "idle'".replace("'", "") else (1 if state == "moving_to_field" else 2)
                # Check if coming from a field with surplus
                tid = getattr(c, "target_id", None)
                surplus = False
                if tid in current_counts:
                    req_tid = getattr(next((f for f in fields if f.id == tid), None), "drones_for_full_protection", 0)
                    if current_counts.get(tid, 0) > req_tid:
                        surplus = True
                # compute eta
                loc = getattr(c, "location", None)
                eta = eta_from_loc_to(loc, tx, ty)
                d2 = dist_sq(loc.x, loc.y, tx, ty) if loc is not None else float("inf")
                # rank tuple: (prefer idle/moving (0), prefer surplus True (0), eta, distance)
                surplus_rank = 0 if surplus else 1
                state_rank = 0 if state == "idle" else (1 if state == "moving_to_field" else 2)
                candidates.append((state_rank, surplus_rank, eta, d2, c))
            candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
            return [t[4] for t in candidates[:k]]

        # Compute fields' needs (excluding top and fully_protected)
        other_fields = [f for f in fields_sorted[1:] if f.id not in fully_protected]
        # Build list of candidate fields we could potentially fully protect with current remaining drones,
        # using only spare drones (idle/moving or from surplus)
        # First compute number of spare drones available (idle/moving or from surplus)
        def is_spare_drone(c):
            if c in decided or c in locked_drones:
                return False
            state = getattr(c, "state", "")
            if state in ("idle", "moving_to_field"):
                return True
            # if protecting, check if its field has surplus
            tid = getattr(c, "target_id", None)
            if tid in current_counts:
                req_tid = getattr(next((f for f in fields if f.id == tid), None), "drones_for_full_protection", 0)
                if current_counts.get(tid, 0) > req_tid:
                    return True
            return False

        spare_pool = [c for c in remaining if is_spare_drone(c)]

        # Greedily fully protect other fields by value-per-drone (threat / need), only if need <= len(spare_pool)
        # Keep re-evaluating spare_pool as we assign
        spare = list(spare_pool)
        # compute current_counts copy for updates
        sim_counts = dict(current_counts)
        while True:
            candidates = []
            for f in other_fields:
                fid = f.id
                req = getattr(f, "drones_for_full_protection", 0)
                have = sim_counts.get(fid, 0)
                need = max(0, req - have)
                if need <= 0:
                    continue
                if need <= len(spare):
                    value = getattr(f, "threat_level", 0) / float(need) if need > 0 else 0
                    candidates.append((value, getattr(f, "threat_level", 0), need, f))
            if not candidates:
                break
            # pick best
            candidates.sort(key=lambda t: (-t[0], -t[1], str(getattr(t[3], "id", ""))))
            value, threat_v, need, chosen_field = candidates[0]
            # pick best 'need' drones from spare
            picked = pick_best_for_field(chosen_field, spare, need)
            if not picked or len(picked) < need:
                break
            # assign them
            for c in picked:
                decided[c] = protecting_group(chosen_field.id)
                if c in spare:
                    spare.remove(c)
                if c in remaining:
                    remaining.remove(c)
                # update sim_counts for their original field if any
                tid = getattr(c, "target_id", None)
                if tid in sim_counts:
                    sim_counts[tid] = max(0, sim_counts.get(tid, 0) - 1)
                sim_counts[chosen_field.id] = sim_counts.get(chosen_field.id, 0) + 1
            # refresh spare as some drones may no longer be spare after counts changed
            spare = [c for c in remaining if is_spare_drone(c)]

        # Any remaining drones -> idle
        for c in components:
            if c not in decided:
                decided[c] = idle_group

        # Assign, with fallback to idle or first group id
        for c, g in decided.items():
            if g not in group_ids:
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
                elif group_ids:
                    environment.assign_group(c, group_ids[0])
                else:
                    pass
            else:
                environment.assign_group(c, g)