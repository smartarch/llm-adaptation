from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track last assigned group per drone and stability counts
        self.prev_group = {}
        self.stable_counts = {}
        # small safety to avoid thrashing immediately
        self.persistence_threshold = 3  # steps considered "stable"

    def _comp_key(self, component):
        for attr in ("id", "name", "uid"):
            if hasattr(component, attr):
                val = getattr(component, attr)
                if val is not None:
                    return f"{attr}:{val}"
        return f"pyid:{id(component)}"

    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize trackers for any new drones
        comp_key_map = {}
        for c in components:
            k = self._comp_key(c)
            comp_key_map[k] = c
            if k not in self.prev_group:
                self.prev_group[k] = "idle"
                self.stable_counts[k] = 0

        # Helper: ensure explicit assignment to group exists
        def safe_assign(comp, grp):
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(comp, grp)
            return grp

        # If no threatened fields, idle everything
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for c in components:
                k = self._comp_key(c)
                assigned = safe_assign(c, "idle")
                # update tracking
                if self.prev_group.get(k) == assigned:
                    self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = assigned
            return

        # Precompute field centers
        field_centers = {}
        for f in threatened_fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_centers[f.id] = (cx, cy)

        # Build drone info
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

        total_drones = len(components)
        half_needed = ceil(total_drones / 2)
        drone_speed = 2.0

        # Helper distance and arrival time
        def distance(k, field_id):
            cx, cy = field_centers[field_id]
            lx, ly = drone_info[k]["loc"]
            return hypot(lx - cx, ly - cy)

        def arrival_time(k, field_id):
            return distance(k, field_id) / drone_speed

        # Compute current protecting counts (based on state and prev_group)
        field_current_protect = {}
        for f in threatened_fields:
            fid = f.id
            cnt = 0
            for k, info in drone_info.items():
                # Treat drone as currently protecting if either state indicates it or previous group shows it
                if (info["state"] == "protecting" and info["target_id"] == fid) or info["prev_group"] == f"protecting {fid}":
                    cnt += 1
            field_current_protect[fid] = cnt

        # Sort threatened fields by descending threat_level (for top selection)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        # Top field guaranteed
        top_field = threatened_fields[0]
        top_required = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
        # Plan allocation dict: field_id -> list of comp_keys
        plan_alloc = defaultdict(list)
        allocated_keys = set()

        # First, allocate for top field, respecting current protectors and movers
        top_group = f"protecting {top_field.id}"
        # candidate keys
        all_keys = set(drone_info.keys())

        # Keep drones already protecting or moving to top field preferentially
        pref_keys = []
        other_keys = []
        for k, info in drone_info.items():
            if info["state"] == "protecting" and info["target_id"] == top_field.id:
                pref_keys.append((0, -info["stable"], k))  # highest priority
            elif info["state"] == "moving_to_field" and info["target_id"] == top_field.id:
                pref_keys.append((1, arrival_time(k, top_field.id), k))
            else:
                other_keys.append(k)
        # sort pref_keys: protecting first, then moving by arrival_time/stability
        pref_sorted = sorted(pref_keys, key=lambda t: (t[0], t[1] if isinstance(t[1], float) else t[1], -drone_info[t[2]]["stable"]) )
        chosen = []
        for item in pref_sorted:
            k = item[-1]
            if len(chosen) >= top_required:
                break
            chosen.append(k)
        if len(chosen) < top_required:
            # fill remaining with best candidates by arrival_time, but avoid moving drones that are very stable on other fields unless necessary
            remaining = [k for k in other_keys if k not in chosen]
            # Rank by (stable_penalty, arrival_time) - prefer lower stable (less sticky) and shorter arrival
            remaining.sort(key=lambda k: (drone_info[k]["stable"], arrival_time(k, top_field.id)))
            need = top_required - len(chosen)
            chosen.extend(remaining[:need])
        # commit chosen for top
        for k in chosen[:top_required]:
            plan_alloc[top_field.id].append(k)
            allocated_keys.add(k)

        # Compute how many protected drones so far
        protected_so_far = sum(len(v) for v in plan_alloc.values())
        # If top wasn't fully filled due to lack of drones, proceed with what we have
        # Now decide additional fields to fully protect to reach half_needed, using per-drone benefit
        # Build candidate list excluding top
        remaining_fields = threatened_fields[1:]
        # For each field compute required and per-drone benefit
        field_benefits = []
        for f in remaining_fields:
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if req <= 0:
                continue
            # benefit per drone: threat_level divided by drones needed
            benefit = getattr(f, "threat_level", 0) / req
            field_benefits.append((benefit, f, req))
        # Sort by descending benefit (higher per-drone value first)
        field_benefits.sort(key=lambda t: t[0], reverse=True)

        # For each candidate field, try to allocate if it helps reach half_needed or has high benefit and we have spare drones
        for benefit, f, req in field_benefits:
            if protected_so_far >= half_needed and len(allocated_keys) + req > total_drones:
                # already satisfied and not enough drones for this field
                continue
            # compute current protectors for this field (prefer them)
            fid = f.id
            current_protectors = []
            movers = []
            others = []
            for k, info in drone_info.items():
                if k in allocated_keys:
                    continue  # already committed
                if info["state"] == "protecting" and info["target_id"] == fid:
                    current_protectors.append(( -info["stable"], k ))  # prefer high stability keepers
                elif info["state"] == "moving_to_field" and info["target_id"] == fid:
                    movers.append((arrival_time(k, fid), k))
                else:
                    others.append(k)
            current_protectors.sort()  # stable desc
            movers.sort()  # arrival asc
            chosen = [k for (_, k) in current_protectors]
            # fill from movers then others, preferring low stable and low arrival
            if len(chosen) < req:
                for _, k in movers:
                    if len(chosen) >= req: break
                    chosen.append(k)
            if len(chosen) < req:
                # rank others by (stable, arrival_time) prefer low stable and close
                others.sort(key=lambda k: (drone_info[k]["stable"], arrival_time(k, fid)))
                need = req - len(chosen)
                chosen.extend(others[:need])
            # If not enough drones available, skip this field
            if len(chosen) < req:
                continue
            # Decide whether to allocate: allocate if it helps reach half_needed or if benefit is high enough
            if protected_so_far < half_needed or benefit > 0:
                # commit chosen
                for k in chosen[:req]:
                    plan_alloc[fid].append(k)
                    allocated_keys.add(k)
                protected_so_far = sum(len(v) for v in plan_alloc.values())
                # stop early if we've used all drones
                if len(allocated_keys) >= total_drones:
                    break

        # Any drones not allocated -> idle
        all_keys = set(drone_info.keys())
        unallocated = all_keys - allocated_keys
        for k in unallocated:
            plan_alloc["idle"].append(k)

        # Final assignments: apply environment.assign_group and update tracking
        for fid, keys in plan_alloc.items():
            if fid == "idle":
                grp = "idle"
            else:
                grp = f"protecting {fid}"
                if grp not in group_ids:
                    grp = "idle"
            for k in keys:
                comp = drone_info[k]["component"]
                assigned_group = safe_assign(comp, grp)
                prev = self.prev_group.get(k)
                if prev == assigned_group:
                    self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = assigned_group