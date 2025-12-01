from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threats to defend against: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {}
        for f in fields_sorted:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Current defenders per field (based on current situation)
        current_counts = {f.id: 0 for f in fields_sorted}
        current_map = {f.id: set() for f in fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_counts:
                    current_counts[tid] = current_counts.get(tid, 0) + 1
                    current_map[tid].add(c)

        final_group = {}  # drone -> group_id
        assigned = set()    # drones already assigned in this step

        # Phase: attempt to fully protect fields in threat order
        for f in fields_sorted:
            required = max(0, getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                # Nothing required to protect; keep current defenders if any
                if current_counts.get(f.id, 0) > 0:
                    for c in current_map.get(f.id, set()):
                        final_group[c] = f"protecting {f.id}"
                        assigned.add(c)
                continue

            current = current_counts.get(f.id, 0)
            need = max(0, required - current)
            if need <= 0:
                # Already fully protected: keep current defenders
                for c in current_map.get(f.id, set()):
                    final_group[c] = f"protecting {f.id}"
                    assigned.add(c)
                continue

            # Allocate closest available drones to this field
            cx, cy = centers[f.id]
            candidates = []
            for c in components:
                if c in assigned:
                    continue
                loc = getattr(c, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float("inf")
                candidates.append((dist2, c))
            candidates.sort(key=lambda t: t[0])

            allocated = 0
            for dist2, drone in candidates:
                if allocated >= need:
                    break
                final_group[drone] = f"protecting {f.id}"
                assigned.add(drone)
                allocated += 1
                current_counts[f.id] = current_counts.get(f.id, 0) + 1

            # Ensure existing defenders for this field are represented in the final plan
            if current_counts.get(f.id, 0) > 0:
                for c in current_map.get(f.id, set()):
                    if c not in assigned:
                        final_group[c] = f"protecting {f.id}"
                        assigned.add(c)

        # Phase: assign all remaining drones to idle
        for c in components:
            if c in final_group:
                environment.assign_group(c, final_group[c])
            else:
                environment.assign_group(c, "idle")