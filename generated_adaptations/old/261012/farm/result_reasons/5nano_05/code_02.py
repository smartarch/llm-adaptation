from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = list(getattr(environment, "fields", []))
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Compute field centers
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # Helper to get current group for a drone
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None):
                return f"protecting {d.target_id}"
            else:
                return "idle"

        # Initial final_group mapping (start with current state)
        final_group = {}
        for d in components:
            final_group[d] = current_group(d)

        # Sort threatened fields by threat level (desc)
        threatened_fields_sorted = sorted(
            threatened_fields,
            key=lambda ff: getattr(ff, "threat_level", 0),
            reverse=True
        )

        # Step 1: Fully protect the most threatened field (top)
        top = threatened_fields_sorted[0]
        top_group = f"protecting {top.id}"
        current_top_protectors = sum(1 for d in components if final_group.get(d) == top_group)
        needed = int(getattr(top, "drones_for_full_protection", 0)) - current_top_protectors
        if needed > 0:
            # Candidates: drones not already protecting the top field
            cx_top, cy_top = field_centers[top.id]
            candidates = []
            for d in components:
                if final_group.get(d) != top_group:
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dx = dy = 0.0
                    else:
                        dx = getattr(loc, "x", 0.0) - cx_top
                        dy = getattr(loc, "y", 0.0) - cy_top
                    dist = sqrt(dx*dx + dy*dy)
                    candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:needed]:
                final_group[d] = top_group

        # Step 2: For remaining fields, try to fully protect them in order
        for f in threatened_fields_sorted[1:]:
            grp = f"protecting {f.id}"
            current_count = sum(1 for d in components if final_group.get(d) == grp)
            needed = int(getattr(f, "drones_for_full_protection", 0)) - current_count
            if needed <= 0:
                continue
            cx, cy = field_centers[f.id]
            # Build candidates not already protecting this field
            candidates = []
            for d in components:
                if final_group.get(d) != grp:
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dx = dy = 0.0
                    else:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                    dist = sqrt(dx*dx + dy*dy)
                    candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:needed]:
                final_group[d] = grp

        # Step 3: Ensure at least half of drones are protecting if possible
        total_drones = len(components)
        half = (total_drones + 1) // 2
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            # Build status for each field
            field_status = []
            for f in threatened_fields_sorted:
                grp = f"protecting {f.id}"
                count = sum(1 for d in components if final_group.get(d) == grp)
                full = count >= int(getattr(f, "drones_for_full_protection", 0))
                field_status.append((f, count, full))
            # Idle drones to reallocate
            idle_drones = [d for d in components if final_group.get(d, "idle") == "idle"]
            # Assign idle drones to the most threatened field that is not full
            for f, count, full in field_status:
                if not idle_drones:
                    break
                if full:
                    continue
                if count >= int(getattr(f, "drones_for_full_protection", 0)):
                    continue
                cx, cy = field_centers[f.id]
                idle_drones.sort(key=lambda d: (
                    (getattr(d.location, "x", 0.0) - cx) ** 2 +
                    (getattr(d.location, "y", 0.0) - cy) ** 2
                ))
                d = idle_drones.pop(0)
                final_group[d] = f"protecting {f.id}"
                current_protectors += 1
                if current_protectors >= half:
                    break

        # Step 4: Final assignment for all drones
        # Ensure every drone has a final group; if not changed, keep as idle
        for d in components:
            grp = final_group.get(d, "idle")
            environment.assign_group(d, grp)