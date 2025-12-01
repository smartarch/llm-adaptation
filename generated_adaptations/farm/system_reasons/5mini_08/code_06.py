from math import hypot, ceil
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev_group = {}
        self.stable_counts = {}

    def _comp_key(self, component):
        for attr in ("id", "name", "uid"):
            if hasattr(component, attr):
                val = getattr(component, attr)
                if val is not None:
                    return f"{attr}:{val}"
        return f"pyid:{id(component)}"

    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize trackers for new drones
        for c in components:
            k = self._comp_key(c)
            if k not in self.prev_group:
                self.prev_group[k] = "idle"
                self.stable_counts[k] = 0

        # Helper to safely assign group
        def safe_assign(comp, grp):
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(comp, grp)
            return grp

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats: idle all drones
            for c in components:
                k = self._comp_key(c)
                assigned = safe_assign(c, "idle")
                if self.prev_group.get(k) == assigned:
                    self.stable_counts[k] += 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = assigned
            return

        # Precompute field centers
        field_centers = {}
        for f in threatened:
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
        speed = 2.0

        def dist(k, field_id):
            cx, cy = field_centers[field_id]
            lx, ly = drone_info[k]["loc"]
            return hypot(lx - cx, ly - cy)

        def arrival(k, field_id):
            return dist(k, field_id) / speed

        # Compute current assignment counts per field (based on prev_group and state)
        field_current = {}
        for f in threatened:
            fid = f.id
            cnt = 0
            members = []
            for k, info in drone_info.items():
                # consider a drone "assigned" to the field if prev_group indicates protecting or it's actively protecting that field
                if info["prev_group"] == f"protecting {fid}" or (info["state"] == "protecting" and info["target_id"] == fid):
                    cnt += 1
                    members.append(k)
            field_current[fid] = {"count": cnt, "members": members}

        # Compute per-field benefit and required values
        fields_data = []
        for f in threatened:
            fid = f.id
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if req <= 0:
                continue
            threat = getattr(f, "threat_level", 0)
            benefit_per_drone = threat / req if req > 0 else 0
            curr = field_current.get(fid, {"count": 0, "members": []})
            fields_data.append({
                "field": f,
                "id": fid,
                "req": req,
                "threat": threat,
                "benefit": benefit_per_drone,
                "current_count": curr["count"],
                "current_members": list(curr["members"])
            })

        # Ensure top field is considered as the most threatened
        fields_data.sort(key=lambda fd: fd["threat"], reverse=True)
        top = fields_data[0]

        # We will choose a set of fields to fully protect.
        # Start by marking fields that are already fully protected (they consume their current members)
        chosen_fields = set()
        allocated_keys = set()
        plan = defaultdict(list)

        # First, ensure top field is chosen (we will fill later)
        chosen_fields.add(top["id"])

        # Keep fully protected fields that already meet requirement (helpful, free)
        # but avoid overriding top decision: we'll keep any field where current_count >= req
        for fd in fields_data:
            if fd["current_count"] >= fd["req"]:
                # Keep them (they consume existing drones)
                chosen_fields.add(fd["id"])
                for k in fd["current_members"]:
                    # we'll trim if the field has more than req members later
                    allocated_keys.add(k)

        # Now greedily add other fields by benefit per drone until drone budget is used or half threshold reached
        # First compute how many drones are effectively reserved by already-chosen fields
        # For chosen fields, we intend to keep up to req members per field from current_members (and fill rest with new drones)
        reserved_so_far = 0
        for fd in fields_data:
            if fd["id"] in chosen_fields:
                # we count min(current_count, req) as reserved; additional required will need allocations
                reserved_so_far += min(fd["current_count"], fd["req"])

        # function to compute additional drones needed for a field given current reserved and members
        def additional_needed(fd):
            # number of drones we will need beyond current_members we can keep
            keep = min(fd["current_count"], fd["req"])
            return fd["req"] - keep

        # compute initial available (unallocated) drones
        unallocated = set(drone_info.keys()) - allocated_keys

        # Greedy by benefit per drone among not-yet-chosen fields (excluding top which is already chosen)
        candidates = [fd for fd in fields_data if fd["id"] not in chosen_fields]
        candidates.sort(key=lambda fd: fd["benefit"], reverse=True)

        # We'll try to add fields while we have drones to spare or until we hit half_needed
        # Compute current_protected_count estimate: sum req for chosen fields (we intend to have these fully protected)
        protected_target = 0
        for fd in fields_data:
            if fd["id"] in chosen_fields:
                protected_target += fd["req"]

        # Ensure top is included; we'll definitely assign its req later
        if top["id"] not in chosen_fields:
            chosen_fields.add(top["id"])
            protected_target += top["req"]

        # Fill with high benefit fields until we either run out of drones or reach half_needed
        for fd in candidates:
            needed = fd["req"]
            # estimate currently available drones: total_drones - (sum of req of chosen fields)
            current_committed = sum(f["req"] for f in fields_data if f["id"] in chosen_fields)
            available_slots = total_drones - current_committed
            if available_slots <= 0:
                break
            if needed <= available_slots or protected_target < half_needed:
                # accept this field
                chosen_fields.add(fd["id"])
                protected_target += fd["req"]

        # At this point chosen_fields is our set we intend to fully protect (must include top).
        # Now select specific drones for each chosen field.
        # Process each chosen field: keep current_members up to req, free low-stability extras, fill rest with best candidates.
        # We'll prefer keepers: those with prev_group protecting this field or moving_to_field with target.
        all_keys = set(drone_info.keys())
        assigned = {}

        # Helper to get candidate ordering for a field
        def rank_candidates_for_field(fid):
            cand = []
            for k in all_keys:
                if k in assigned:
                    continue
                info = drone_info[k]
                # score tuples: prefer currently protecting, then moving_to_field, then low stability & short arrival
                is_protecting = (info["state"] == "protecting" and info["target_id"] == fid) or (info["prev_group"] == f"protecting {fid}")
                is_moving = (info["state"] == "moving_to_field" and info["target_id"] == fid)
                # rank key: (priority, stable, arrival)
                if is_protecting:
                    priority = 0
                elif is_moving:
                    priority = 1
                else:
                    priority = 2
                # stable: prefer lower stable (less costly to move) after protecting/moving distinction
                stable = info["stable"]
                arrival_time = arrival(k, fid)
                cand.append((priority, stable, arrival_time, k))
            cand.sort(key=lambda t: (t[0], t[1], t[2]))
            return [t[3] for t in cand]

        # Before assigning, handle overprotection: if a currently chosen field has more current_members than req, free extras (prefer low-stable extras)
        for fd in fields_data:
            fid = fd["id"]
            if fid not in chosen_fields:
                continue
            req = fd["req"]
            current_members = list(fd["current_members"])
            if len(current_members) <= req:
                # keep all current members (they'll be used), mark them as assigned candidates
                for k in current_members:
                    assigned[k] = f"protecting {fid}"
            else:
                # choose which to keep: prefer high stability and those actually protecting
                def member_score(k):
                    info = drone_info[k]
                    is_actually_protecting = (info["state"] == "protecting" and info["target_id"] == fid)
                    # keep those actually protecting and with high stability
                    return (0 if is_actually_protecting else 1, -info["stable"], -int(is_actually_protecting))
                current_members.sort(key=member_score)
                keep = current_members[:req]
                free = current_members[req:]
                for k in keep:
                    assigned[k] = f"protecting {fid}"
                # freed drones become unassigned for selection
                for k in free:
                    if k in assigned:
                        del assigned[k]

        # Now fill remaining slots per chosen field
        for fd in fields_data:
            fid = fd["id"]
            if fid not in chosen_fields:
                continue
            req = fd["req"]
            already = [k for k, g in assigned.items() if g == f"protecting {fid}"]
            need = req - len(already)
            if need <= 0:
                continue
            # get ranked candidates
            ranked = rank_candidates_for_field(fid)
            # pick first need that are not already assigned
            picked = []
            for k in ranked:
                if k in assigned:
                    continue
                picked.append(k)
                if len(picked) >= need:
                    break
            for k in picked:
                assigned[k] = f"protecting {fid}"

        # All unassigned drones go to idle or optionally be used to partially help non-chosen fields? We prefer idle to avoid ineffective partial protection.
        for k in all_keys:
            if k not in assigned:
                assigned[k] = "idle"

        # Ensure we used at least half the drones for protection if feasible:
        protecting_count = sum(1 for g in assigned.values() if g != "idle")
        if protecting_count < half_needed:
            # attempt to add additional best drones to highest-benefit chosen fields (without exceeding req)
            # gather fields needing extra drones (maybe because we couldn't fill earlier)
            # prefer fields by benefit
            chosen_list = [fd for fd in fields_data if fd["id"] in chosen_fields]
            chosen_list.sort(key=lambda fd: fd["benefit"], reverse=True)
            free_keys = [k for k, g in assigned.items() if g == "idle"]
            free_keys.sort(key=lambda k: drone_info[k]["stable"])  # prefer low-stability drones to move
            for fd in chosen_list:
                if protecting_count >= half_needed:
                    break
                fid = fd["id"]
                req = fd["req"]
                cur = sum(1 for g in assigned.values() if g == f"protecting {fid}")
                can_add = req - cur
                if can_add <= 0:
                    continue
                # pick up to can_add from free_keys by arrival time
                free_keys.sort(key=lambda k: arrival(k, fid))
                to_move = free_keys[:can_add]
                for k in to_move:
                    assigned[k] = f"protecting {fid}"
                free_keys = [k for k in free_keys if k not in to_move]
                protecting_count = sum(1 for g in assigned.values() if g != "idle")

        # Apply assignments
        for k, grp in assigned.items():
            comp = drone_info[k]["component"]
            assigned_group = safe_assign(comp, grp)
            prev = self.prev_group.get(k)
            if prev == assigned_group:
                self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
            else:
                self.stable_counts[k] = 1
            self.prev_group[k] = assigned_group