from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Precompute field centers and sort fields by threat level (high to low)
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        plan = {}        # index -> target group
        allocated = set()  # indices already allocated to a group

        # Phase 1: Full protection where possible, preserving existing protectors
        for f in threat_fields_sorted:
            field_group = f"protecting {f.id}"
            cx, cy = centers[f.id]

            # Current protectors for this field (should stay in this field)
            current_protect_indices = [
                i for i, c in enumerate(components)
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            for idx in current_protect_indices:
                plan[idx] = field_group
                allocated.add(idx)

            current_count = len(current_protect_indices)
            needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_count)
            if needed <= 0:
                continue

            # Find nearest available drones to this field's center
            candidates = [i for i in range(len(components)) if i not in allocated]
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

            # Allocate up to 'needed' drones (closest)
            for _, idx in dist_list[:needed]:
                plan[idx] = field_group
                allocated.add(idx)

        # Phase 2: Distribute remaining drones to partially protect fields
        remaining = [i for i in range(len(components)) if i not in allocated]

        for f in threat_fields_sorted:
            field_group = f"protecting {f.id}"
            cx, cy = centers[f.id]

            # Current number allocated to this field in the plan
            current_in_plan = sum(1 for i in plan if plan[i] == field_group)
            needed_partial = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_in_plan)
            if needed_partial <= 0:
                continue

            if not remaining:
                break

            # Allocate from the closest remaining drones
            dist_list = []
            for idx in remaining:
                loc = getattr(components[idx], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    d2 = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    d2 = dx*dx + dy*dy
                dist_list.append((d2, idx))
            dist_list.sort(key=lambda t: t[0])

            for _, idx in dist_list[:needed_partial]:
                plan[idx] = field_group
                allocated.add(idx)

            # Update remaining after this field
            remaining = [i for i in range(len(components)) if i not in allocated]

        # Final assignment: every drone must be in a group
        for i, drone in enumerate(components):
            if i in plan:
                environment.assign_group(drone, plan[i])
            else:
                environment.assign_group(drone, "idle")