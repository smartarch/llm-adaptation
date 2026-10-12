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

        # Order fields by descending threat level
        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {}
        for f in fields_sorted:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            centers[f.id] = (cx, cy)

        # Current protection counts per field
        current_counts = {f.id: 0 for f in fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_counts:
                    current_counts[tid] = current_counts.get(tid, 0) + 1

        final_assignment = {}  # drone -> group_id
        allocated = set()     # drones already assigned in this step

        # Step through fields: attempt to fully protect as many as possible
        for f in fields_sorted:
            full_needed = getattr(f, "drones_for_full_protection", 0)
            if full_needed <= 0:
                # If for some reason no drones are required, ensure any current defenders stay assigned
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        final_assignment[c] = f"protecting {f.id}"
                        allocated.add(c)
                continue

            current = current_counts.get(f.id, 0)
            need = max(0, full_needed - current)
            if need <= 0:
                # Field already fully protected: ensure its defenders stay in place
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        final_assignment[c] = f"protecting {f.id}"
                        allocated.add(c)
                continue

            # Build candidate drones: those not currently protecting this field
            cx, cy = centers[f.id]
            candidates = []
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                    # Skip drones already protecting this field
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

            # Allocate up to 'need' drones from candidates (respecting already allocated drones)
            used_this_field = 0
            for dist2, drone in candidates:
                if drone in allocated:
                    continue
                final_assignment[drone] = f"protecting {f.id}"
                allocated.add(drone)
                current_counts[f.id] = current_counts.get(f.id, 0) + 1
                used_this_field += 1
                if used_this_field >= need:
                    break

        # Step 4: assign any drones not yet assigned to idle
        for c in components:
            if c in final_assignment:
                environment.assign_group(c, final_assignment[c])
            else:
                environment.assign_group(c, "idle")