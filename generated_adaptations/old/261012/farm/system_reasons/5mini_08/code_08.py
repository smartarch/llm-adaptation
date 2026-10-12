from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track previous group assignment and consecutive steps count
        self.prev_group = {}
        self.stable_counts = {}

    def _comp_key(self, component):
        # prefer any obvious id attribute else python id
        for attr in ("id", "name", "uid"):
            if hasattr(component, attr):
                val = getattr(component, attr)
                if val is not None:
                    return f"{attr}:{val}"
        return f"pyid:{id(component)}"

    def assign_drones(self, components, environment, group_ids, step: int):
        # initialize trackers for new drones
        for c in components:
            k = self._comp_key(c)
            if k not in self.prev_group:
                self.prev_group[k] = "idle"
                self.stable_counts[k] = 0

        # helper to ensure valid group assignment
        def do_assign(comp, grp):
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(comp, grp)
            return grp

        # gather threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # no threat: idle all drones
            for c in components:
                k = self._comp_key(c)
                assigned = do_assign(c, "idle")
                if self.prev_group.get(k) == assigned:
                    self.stable_counts[k] += 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = assigned
            return

        # precompute field centers
        field_centers = {}
        for f in fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_centers[f.id] = (cx, cy)

        # gather drone info
        drone_info = {}
        for c in components:
            k = self._comp_key(c)
            lx = getattr(c.location, "x", 0)
            ly = getattr(c.location, "y", 0)
            drone_info[k] = {
                "component": c,
                "loc": (lx, ly),
                "state": getattr(c, "state", None),
                "target_id": getattr(c, "target_id", None),
                "prev_group": self.prev_group.get(k, "idle"),
                "stable": self.stable_counts.get(k, 0)
            }

        all_keys = set(drone_info.keys())
        total_drones = len(components)
        half_needed = ceil(total_drones / 2)
        speed = 2.0

        # distance and arrival helpers
        def dist(k, field_id):
            cx, cy = field_centers[field_id]
            lx, ly = drone_info[k]["loc"]
            return hypot(lx - cx, ly - cy)

        def arrival(k, field_id):
            return dist(k, field_id) / speed

        # sort fields by threat descending to find top
        fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = fields[0]
        top_req = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))

        # plan allocations: field_id -> list of drone keys (component keys); "idle" key for idle drones
        plan = defaultdict(list)
        assigned_keys = set()

        # helper to rank drones for a particular field
        def rank_for_field(fid):
            ranked = []
            for k in all_keys:
                if k in assigned_keys:
                    continue
                info = drone_info[k]
                # priority: 0 if already protecting this field (or prev_group says protecting), 1 if moving to it, 2 otherwise
                already_protecting = (info["state"] == "protecting" and info["target_id"] == fid) or (info["prev_group"] == f"protecting {fid}")
                moving_to = (info["state"] == "moving_to_field" and info["target_id"] == fid)
                if already_protecting:
                    priority = 0
                elif moving_to:
                    priority = 1
                else:
                    priority = 2
                # For priority==0 prefer higher stable (keep stable assignments), for others prefer lower stable to avoid breaking stable ones
                stable = info["stable"]
                arr = arrival(k, fid)
                # Compose sort key: prefer lower priority, then (for priority 0) -stable (keep), else stable (move low-stable), then arrival
                if priority == 0:
                    key = (0, -stable, arr, k)
                else:
                    key = (1, stable, arr, k)
                ranked.append(key)
            ranked.sort()
            return [t[3] for t in ranked]

        # 1) Fill top field first: choose top_req drones with the best rank (this will favor keepers & movers & closest)
        top_candidates = rank_for_field(top_field.id)
        chosen_top = top_candidates[:top_req]
        for k in chosen_top:
            plan[top_field.id].append(k)
            assigned_keys.add(k)

        # 2) Determine remaining drones and whether we meet half_needed
        protecting_count = sum(len(v) for v in plan.values())
        # Select additional fields by benefit-per-drone descending (threat / req)
        extras = []
        for f in fields[1:]:
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if req <= 0:
                continue
            benefit = getattr(f, "threat_level", 0) / req if req > 0 else 0
            extras.append((benefit, f))
        extras.sort(key=lambda x: x[0], reverse=True)

        # Greedily add extra fields until we either reach half_needed or run out of reasonable options
        for benefit, f in extras:
            if protecting_count >= half_needed:
                break
            fid = f.id
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            # If not enough unassigned drones to fill this field, skip
            if len(all_keys - assigned_keys) < req:
                continue
            # choose best drones for this field using ranking
            candidates = rank_for_field(fid)
            chosen = candidates[:req]
            for k in chosen:
                plan[fid].append(k)
                assigned_keys.add(k)
            protecting_count = sum(len(v) for v in plan.values())

        # If after attempting extras we still have protecting_count < half_needed, try to add more fields (by threat order)
        if protecting_count < half_needed:
            for f in fields[1:]:
                fid = f.id
                if fid in plan:
                    continue
                req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
                if req <= 0:
                    continue
                if len(all_keys - assigned_keys) < req:
                    continue
                # choose best drones
                candidates = rank_for_field(fid)
                chosen = candidates[:req]
                for k in chosen:
                    plan[fid].append(k)
                    assigned_keys.add(k)
                protecting_count = sum(len(v) for v in plan.values())
                if protecting_count >= half_needed:
                    break

        # Ensure we never over-assign per field (trim if somehow more assigned)
        for f in fields:
            fid = f.id
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if len(plan[fid]) > req:
                # prefer to keep ones that were already protecting (higher priority)
                def keeper_score(k):
                    info = drone_info[k]
                    already_protecting = (info["state"] == "protecting" and info["target_id"] == fid) or (info["prev_group"] == f"protecting {fid}")
                    return (0 if already_protecting else 1, -info["stable"])
                plan[fid].sort(key=keeper_score)
                # keep first req
                to_keep = plan[fid][:req]
                to_free = set(plan[fid][req:])
                plan[fid] = to_keep
                for k in to_free:
                    assigned_keys.discard(k)

        # Remaining unassigned drones -> idle
        for k in (all_keys - assigned_keys):
            plan["idle"].append(k)

        # Final assignment to environment and update trackers
        for fid, keys in plan.items():
            if fid == "idle":
                grp = "idle"
            else:
                grp = f"protecting {fid}"
                if grp not in group_ids:
                    grp = "idle"
            for k in keys:
                comp = drone_info[k]["component"]
                assigned_group = do_assign(comp, grp)
                prev = self.prev_group.get(k)
                if prev == assigned_group:
                    self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = assigned_group