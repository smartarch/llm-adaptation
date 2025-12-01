from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        n = len(components)

        # 2) Precompute field centers
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # 3) Sort fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        plan = {}        # drone_index -> group
        allocated = set()

        # Phase A: preserve existing protectors
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            for i, c in enumerate(components):
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                    plan[i] = group
                    allocated.add(i)

        # Phase B: full protection where possible (respecting current protectors)
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            cx, cy = centers[f.id]
            cap = int(getattr(f, "drones_for_full_protection", 0))

            # current protectors for this field
            current_indices = [
                i for i, c in enumerate(components)
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            current_count = len(current_indices)
            needed = max(0, cap - current_count)
            if needed <= 0:
                continue

            # pick closest available drones
            candidates = [i for i in range(n) if i not in allocated]
            if not candidates:
                break

            dist_list = []
            for idx in candidates:
                loc = getattr(components[idx], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    d2 = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    d2 = dx*dx + dy*dy
                dist_list.append((d2, idx))
            dist_list.sort(key=lambda t: t[0])

            for _, idx in dist_list[:needed]:
                plan[idx] = group
                allocated.add(idx)

        # Phase C: distribute remaining drones across fields in passes by threat order and proximity
        remaining = set(i for i in range(n)) - allocated
        while remaining:
            progressed = False
            for f in threat_fields_sorted:
                if not remaining:
                    break
                group = f"protecting {f.id}"
                cx, cy = centers[f.id]

                # choose the closest remaining drone
                best_idx = None
                best_dist = float("inf")
                for idx in list(remaining):
                    loc = getattr(components[idx], "location", None)
                    if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                        continue
                    d = (loc.x - cx)**2 + (loc.y - cy)**2
                    if d < best_dist:
                        best_dist = d
                        best_idx = idx

                if best_idx is not None:
                    plan[best_idx] = group
                    allocated.add(best_idx)
                    remaining.remove(best_idx)
                    progressed = True

            if not progressed:
                break

        # Final assignment: every drone must be in a group
        for i, drone in enumerate(components):
            environment.assign_group(drone, plan.get(i, "idle"))