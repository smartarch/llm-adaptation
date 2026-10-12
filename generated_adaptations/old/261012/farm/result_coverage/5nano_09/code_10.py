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
        fields_by_id = {f.id: f for f in fields_sorted}

        # 3) Current protection counts per field
        current_counts = {fid: 0 for fid in fields_by_id}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in current_counts:
                    current_counts[tid] += 1

        # Track allocations
        assigned = set()

        # Helper: center of a field
        def field_center(f):
            cx = (getattr(f, "left", 0.0) + getattr(f, "right", 0.0)) / 2.0
            cy = (getattr(f, "top", 0.0) + getattr(f, "bottom", 0.0)) / 2.0
            return cx, cy

        # Helper: distance squared from drone to field center
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
        partial_protectors = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None]

        # Stage A: attempt to fully protect fields in threat order
        for f in fields_sorted:
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

            # If no drones available, skip
            if not idle and not partial_protectors:
                continue

            candidates = []

            # Prefer idle drones first
            if idle:
                candidates.extend(idle)

            # Safe steal candidates: from fields with lower threat that are not yet fully protected
            if partial_protectors:
                for d in partial_protectors:
                    tid = getattr(d, "target_id", None)
                    if tid is None or tid == fid:
                        continue
                    other = fields_by_id.get(tid)
                    if other is None:
                        continue
                    if getattr(other, "threat_level", 0) < getattr(f, "threat_level", 0):
                        if current_counts.get(tid, 0) < int(getattr(other, "drones_for_full_protection", 0)):
                            candidates.append(d)

            # Deduplicate
            seen = set()
            uniq = []
            for c in candidates:
                if id(c) not in seen:
                    uniq.append(c)
                    seen.add(id(c))
            candidates = uniq

            if not candidates:
                continue

            # Choose closest candidates
            candidates.sort(key=lambda dr: dist_to_field_sq(dr, f))
            take = min(need, len(candidates))
            for i in range(take):
                d = candidates[i]
                environment.assign_group(d, pid)
                assigned.add(d)
                if d in idle:
                    idle.remove(d)
                if d in partial_protectors:
                    src = getattr(d, "target_id", None)
                    if src and src in current_counts:
                        current_counts[src] = max(0, current_counts[src] - 1)
                current_counts[fid] = current_counts.get(fid, 0) + 1

        # Stage B: ensure any fully-protected fields have their protectors in the correct group
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in fields_by_id:
                    pid = f"protecting {tid}"
                    if pid in group_ids:
                        environment.assign_group(d, pid)
                        assigned.add(d)

        # Stage C: any remaining drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")