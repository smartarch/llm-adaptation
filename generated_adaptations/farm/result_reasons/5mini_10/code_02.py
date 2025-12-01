from math import ceil, sqrt
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # persistent state across adaptation steps
        # mapping drone_key -> last assigned group name
        self.last_assignment = {}
        # mapping drone_key -> consecutive steps stayed in last_assignment
        self.stay_counts = defaultdict(int)
        # small safety: track last step assigned (not strictly necessary but handy)
        self.last_step = None

    def _drone_key(self, comp):
        # try to use a stable id if present, otherwise Python id
        return getattr(comp, "id", id(comp))

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, point):
        dx = loc.x - point[0]
        dy = loc.y - point[1]
        return sqrt(dx * dx + dy * dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize step tracking
        if self.last_step is None or step != self.last_step + 1:
            # If non-consecutive or first step, we don't attempt to infer long history
            # but keep existing counters (they may still be meaningful)
            pass
        self.last_step = step

        # Collect relevant fields (threat > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: assign all drones to idle
            for comp in components:
                environment.assign_group(comp, "idle")
                key = self._drone_key(comp)
                prev = self.last_assignment.get(key)
                if prev == "idle":
                    self.stay_counts[key] += 1
                else:
                    self.stay_counts[key] = 1
                self.last_assignment[key] = "idle"
            return

        # sort fields by descending threat_level (tie-breaker: id)
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # compute the required drones for each field (ceil)
        field_requirements = {}
        for f in threatened_fields:
            try:
                req = int(ceil(float(f.drones_for_full_protection)))
            except Exception:
                # fallback: at least 1 drone
                req = 1
            if req < 1:
                req = 1
            field_requirements[f.id] = req

        # Precompute centers
        field_centers = {f.id: self._field_center(f) for f in threatened_fields}

        # Build helper lists of components with metadata
        drone_info = []
        for comp in components:
            key = self._drone_key(comp)
            loc = comp.location
            drone_info.append({
                "comp": comp,
                "key": key,
                "state": getattr(comp, "state", None),
                "target_id": getattr(comp, "target_id", None),
                "loc": loc,
                "last_group": self.last_assignment.get(key),
                "stay": int(self.stay_counts.get(key, 0))
            })

        # Which group names are valid? We'll create group name strings and verify membership in group_ids
        valid_group_set = set(group_ids)

        # Allocation result: mapping drone_key -> group_name
        allocation = {}

        total_drones = len(components)
        # target: at least half drones used for protection when possible
        min_protect_drones = max(1, int(ceil(total_drones / 2.0)))

        # Sticky threshold: prefer not to move drones that have been staying for this many steps
        sticky_threshold = 3

        # Helper: mark drone allocated
        allocated_keys = set()

        # Function to pick candidates for a given field up to needed count
        def fill_field(field, needed, allocated_keys):
            field_id = field.id
            center = field_centers[field_id]

            selected = []

            # 1) Keep drones already protecting this field (state == protecting and target_id == field.id)
            for d in drone_info:
                if d["key"] in allocated_keys:
                    continue
                if d["state"] == "protecting" and d["target_id"] == field_id:
                    selected.append((0, 0, 0.0, d))  # highest priority
            # 2) moving_to_field with same target
            for d in drone_info:
                if d["key"] in allocated_keys:
                    continue
                if d["state"] == "moving_to_field" and d["target_id"] == field_id:
                    dist = self._distance(d["loc"], center)
                    # priority for moving_to_target
                    selected.append((1, d["stay"], dist, d))
            # 3) other candidates: idle, protecting other, moving to other -> rank and sort by (rank, stay penalty, dist)
            others = []
            for d in drone_info:
                if d["key"] in allocated_keys:
                    continue
                # skip those already added (protecting this field)
                if d["state"] == "protecting" and d["target_id"] == field_id:
                    continue
                if d["state"] == "moving_to_field" and d["target_id"] == field_id:
                    continue
                dist = self._distance(d["loc"], center)
                if d["state"] == "idle":
                    rank = 2
                elif d["state"] == "moving_to_field":
                    rank = 3
                else:
                    # protecting other field
                    rank = 4
                others.append((rank, d["stay"], dist, d))
            # sort others by rank, then prefer lower stay (less sticky), then closer
            others.sort(key=lambda t: (t[0], t[1], t[2]))
            selected.extend(others)

            # Now take up to needed distinct drones
            chosen = []
            seen = set()
            for entry in selected:
                d = entry[3]
                k = d["key"]
                if k in seen:
                    continue
                seen.add(k)
                chosen.append(d)
                if len(chosen) >= needed:
                    break
            # Mark them allocated and return list
            for d in chosen:
                allocated_keys.add(d["key"])
            return chosen

        # 1) Fill the most threatened field fully, using closest & sticky-aware selection
        most_threatened = threatened_fields[0]
        req_most = field_requirements[most_threatened.id]

        chosen_for_most = fill_field(most_threatened, req_most, allocated_keys)

        # If we couldn't pick enough (fewer drones available than req), we still assign as many as possible.
        # Mark them in allocation
        for d in chosen_for_most:
            allocation[d["key"]] = f"protecting {most_threatened.id}"

        # 2) After securing most threatened, try to allocate remaining to other fields (in threat order)
        # but prioritize meeting min_protect_drones total.
        currently_assigned_protection = len(chosen_for_most)
        remaining_to_achieve_min = max(0, min_protect_drones - currently_assigned_protection)

        # For each subsequent field, attempt to fully protect it but stop early if we've reached the target protection count
        for field in threatened_fields[1:]:
            if remaining_to_achieve_min <= 0 and len(allocated_keys) >= min_protect_drones:
                break
            req = field_requirements[field.id]
            # but if req is large and fewer drones are available, we may only partially fill; still prefer full protection,
            # so only allocate if we can allocate all req or we still need drones to satisfy min_protect_drones.
            available_unallocated = [d for d in drone_info if d["key"] not in allocated_keys]
            max_available = len(available_unallocated)
            if max_available <= 0:
                break
            # decide how many to try to allocate: either full req if possible or as many as needed to meet min_protect_drones
            if max_available >= req:
                needed = req
            else:
                # allocate what's available only if we still need to reach min_protect_drones
                if remaining_to_achieve_min > 0:
                    needed = min(max_available, remaining_to_achieve_min)
                else:
                    needed = 0
            if needed <= 0:
                continue
            chosen = fill_field(field, needed, allocated_keys)
            for d in chosen:
                allocation[d["key"]] = f"protecting {field.id}"
            currently_assigned_protection += len(chosen)
            remaining_to_achieve_min = max(0, min_protect_drones - currently_assigned_protection)

        # 3) Any drones that are currently protecting fields that we did not explicitly keep allocated and are not allocated yet:
        # try to keep them where they are if that doesn't conflict with "no overprotection" and stickiness.
        # This handles the case where some protecting drones were not chosen earlier but are already protecting some field;
        # we give preference to keep them if their field still needs them and they are sticky.
        # Build map field->count already allocated
        allocated_count_by_field = defaultdict(int)
        for grp in allocation.values():
            if grp.startswith("protecting "):
                fid = grp[len("protecting "):]
                allocated_count_by_field[fid] += 1

        for d in drone_info:
            k = d["key"]
            if k in allocation:
                continue  # already allocated
            # if drone is protecting some field, consider keeping it if that field has not exceeded requirement
            if d["state"] == "protecting" and d["target_id"] is not None:
                fid = d["target_id"]
                if str(fid) in allocated_count_by_field:
                    # careful: field ids may be ints or strings; we compare string-ified ids in allocation keys earlier
                    # but our allocated_count_by_field currently used string keys from allocation; ensure consistent:
                    pass
                # Convert to same type: in allocation keys we used f"{field.id}" which stringifies id.
                fid_str = str(fid)
                # find matching field object to get requirement
                matching_field = next((f for f in threatened_fields if str(f.id) == fid_str), None)
                if matching_field:
                    req = field_requirements[matching_field.id]
                    if allocated_count_by_field[fid_str] < req:
                        # keep this drone protecting that field
                        allocation[k] = f"protecting {matching_field.id}"
                        allocated_count_by_field[fid_str] += 1
                        allocated_keys.add(k)

        # 4) Any remaining unallocated drones -> idle
        for d in drone_info:
            k = d["key"]
            if k not in allocation:
                allocation[k] = "idle"

        # 5) Now apply assignments via environment.assign_group, ensuring group_id exists
        for d in drone_info:
            comp = d["comp"]
            k = d["key"]
            desired_group = allocation.get(k, "idle")
            # validate group exists; if not, fallback to "idle"
            if desired_group not in valid_group_set:
                desired_group = "idle"
            environment.assign_group(comp, desired_group)
            # update persistent state: last_assignment and stay_counts
            prev = self.last_assignment.get(k)
            if prev == desired_group:
                self.stay_counts[k] = int(self.stay_counts.get(k, 0)) + 1
            else:
                self.stay_counts[k] = 1
            self.last_assignment[k] = desired_group