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
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in current_counts:
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
        # Drones currently protecting some field that is NOT yet fully protected
        non_full_protectors = [d for d in components if getattr(d, "state", None) == "protecting" 
                               and getattr(d, "target_id", None) is not None
                               and any((tid != d.target_id for tid in current_counts))]
        # Stage A: Fully protect fields in threat order
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
            if not idle and not non_full_protectors:
                continue

            # Build candidate pool (safe reallocations)
            candidates = []

            # Prefer idle drones first
            candidates.extend(idle)

            # Safe steals: from fields with lower threat that are not yet fully protected
            for d in non_full_protectors:
                tid = getattr(d, "target_id", None)
                if tid is None or tid == fid:
                    continue
                other = field_by_id.get(tid)
                if other is None:
                    continue
                if getattr(other, "threat_level", 0) <= getattr(f, "threat_level", 0):
                    # If other field is not yet fully protected
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
                if d in non_full_protectors:
                    # Update count for the field this drone was previously protecting
                    prev_tid = getattr(d, "target_id", None)
                    if prev_tid is not None and prev_tid in current_counts:
                        current_counts[prev_tid] = max(0, current_counts[prev_tid] - 1)
                # Update count for this field
                current_counts[fid] = current_counts.get(fid, 0) + 1

        # Stage B: After attempting full protections, ensure any fully protected fields have their protectors in the correct group
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    pid = f"protecting {tid}"
                    if pid in group_ids:
                        environment.assign_group(d, pid)
                        assigned.add(d)

        # Stage C: Any remaining drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")