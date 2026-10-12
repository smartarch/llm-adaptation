from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat (highest first)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        field_by_id = {f.id: f for f in fields_sorted}

        # 3) Current protection counts per field
        current_counts = {f.id: 0 for f in fields_sorted}
        protect_by_field = {f.id: [] for f in fields_sorted}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in current_counts:
                    protect_by_field[tid].append(d)
                    current_counts[tid] += 1

        # Track allocations
        assigned = set()

        # Helpers
        def field_center(f):
            cx = (getattr(f, "left", 0.0) + getattr(f, "right", 0.0)) / 2.0
            cy = (getattr(f, "top", 0.0) + getattr(f, "bottom", 0.0)) / 2.0
            return cx, cy

        def dist_to_field_sq(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = field_center(f)
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return dx * dx + dy * dy

        # Pools
        idle = [d for d in components if getattr(d, "state", None) == "idle"]

        # Stage A: determine the maximum set of fields we can fully protect
        total_drones = len(components)
        full_set = []
        needed_so_far = 0
        for f in fields_sorted:
            fid = f.id
            current = current_counts.get(fid, 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - current)
            if need <= 0:
                continue
            if needed_so_far + need <= total_drones:
                full_set.append(f)
                needed_so_far += need
            else:
                break

        # Stage A: allocate to full_set fields
        for f in full_set:
            fid = f.id
            pid = f"protecting {fid}"
            if pid not in group_ids:
                continue

            current = current_counts.get(fid, 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - current)
            if need <= 0:
                # Ensure current protectors for this field are in the correct group
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, pid)
                        assigned.add(d)
                continue

            # Use idle drones first
            take_idle = min(need, len(idle))
            for _ in range(take_idle):
                d = idle.pop(0)
                environment.assign_group(d, pid)
                assigned.add(d)
                current_counts[fid] = current_counts.get(fid, 0) + 1
            need -= take_idle

            if need <= 0:
                continue

            # Safe steals: from fields with non-full protection and lower threat
            candidates = []
            for other in fields_sorted:
                if other.id == fid:
                    continue
                if getattr(other, "threat_level", 0) < getattr(f, "threat_level", 0):
                    other_count = current_counts.get(other.id, 0)
                    if other_count > 1:
                        candidates.append(other.id)

            # Deduplicate and sort by threat ascending
            candidates = sorted(set(candidates), key=lambda oid: getattr(field_by_id[oid], "threat_level", 0))

            for other_id in candidates:
                if need <= 0:
                    break
                cap = current_counts.get(other_id, 0) - 1
                while cap > 0 and need > 0 and protect_by_field.get(other_id):
                    d = protect_by_field[other_id].pop()
                    environment.assign_group(d, pid)
                    assigned.add(d)
                    current_counts[other_id] -= 1
                    current_counts[fid] += 1
                    need -= 1
                    cap -= 1

        # Stage B: ensure fully protected fields have their protectors in the correct group
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    pid = f"protecting {tid}"
                    if pid in group_ids:
                        environment.assign_group(d, pid)
                        assigned.add(d)

        # Stage C: partial protection - distribute remaining idle drones to next-high threat fields
        needs = []
        for f in fields_sorted:
            fid = f.id
            pid = f"protecting {fid}"
            if pid not in group_ids:
                continue
            need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_counts.get(fid, 0))
            if need > 0:
                needs.append((f, need))
        while idle and needs:
            needs.sort(key=lambda t: getattr(t[0], "threat_level", 0), reverse=True)
            f, need = needs[0]
            if need <= 0:
                needs.pop(0)
                continue
            # closest idle drone
            best_idx = -1
            best_dist = float("inf")
            for idx, d in enumerate(idle):
                dists = dist_to_field_sq(d, f)
                if dists < best_dist:
                    best_dist = dists
                    best_idx = idx
            if best_idx == -1:
                break
            d = idle.pop(best_idx)
            environment.assign_group(d, f"protecting {f.id}")
            assigned.add(d)
            current_counts[f.id] = current_counts.get(f.id, 0) + 1
            need -= 1
            needs[0] = (f, need)
            if need <= 0:
                needs.pop(0)

        # Stage D: any remaining drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")