from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low)
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers
        centers = {}
        for f in fields_sorted:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Current defenders per field
        current_counts = {f.id: 0 for f in fields_sorted}
        current_map = {f.id: set() for f in fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_counts:
                    current_counts[tid] = current_counts.get(tid, 0) + 1
                    current_map[tid].add(c)

        final_group = {}  # drone -> group_id
        assigned = set()  # drones already assigned in this step

        # Phase 1: attempt to fully protect as many fields as possible (greedy by threat)
        for f in fields_sorted:
            required = max(0, getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                # Nothing required to protect; keep current defenders if any
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

            # Allocate closest available drones
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
                    dist2 = float('inf')
                candidates.append((dist2, c))
            candidates.sort(key=lambda t: t[0])

            allocated_this_field = 0
            for dist2, drone in candidates:
                if allocated_this_field >= need:
                    break
                final_group[drone] = f"protecting {f.id}"
                assigned.add(drone)
                allocated_this_field += 1
                current_counts[f.id] = current_counts.get(f.id, 0) + 1

            # If there are already defenders, ensure they are mapped
            if current_counts.get(f.id, 0) > 0:
                for c in current_map.get(f.id, set()):
                    if c not in assigned:
                        final_group[c] = f"protecting {f.id}"
                        assigned.add(c)

        # Phase 2: use remaining drones to provide partial protection to next-highest fields
        # Build list of fields that are not yet fully protected
        not_full = []
        for f in fields_sorted:
            required = max(0, getattr(f, "drones_for_full_protection", 0))
            current = current_counts.get(f.id, 0)
            if required > current:
                not_full.append((f.threat_level, f))
        not_full.sort(key=lambda t: t[0], reverse=True)
        unassigned = [c for c in components if c not in assigned]

        for _, f in not_full:
            if not unassigned:
                break
            cx, cy = centers[f.id]
            best_idx = None
            best_dist = float('inf')
            for idx, drone in enumerate(unassigned):
                loc = getattr(drone, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist2 = dx*dx + dy*dy
                else:
                    dist2 = float('inf')
                if dist2 < best_dist:
                    best_dist = dist2
                    best_idx = idx
            if best_idx is not None:
                drone = unassigned.pop(best_idx)
                final_group[drone] = f"protecting {f.id}"
                assigned.add(drone)
                current_counts[f.id] = current_counts.get(f.id, 0) + 1

        # Phase 3: assign all others to idle
        for c in components:
            if c in final_group:
                environment.assign_group(c, final_group[c])
            else:
                environment.assign_group(c, "idle")